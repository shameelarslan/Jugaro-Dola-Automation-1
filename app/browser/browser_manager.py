import os
import time
import traceback
from pathlib import Path
from playwright.sync_api import sync_playwright, Playwright, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError
from config import (
    ACCOUNTS_DIR,
    DEFAULT_DEBUG_MODE,
    DEFAULT_HEADLESS,
    DEFAULT_SLOW_MO,
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_DESKTOP_VIEWPORT,
    DEFAULT_DESKTOP_USER_AGENT,
    FB_DESKTOP_URL,
)
from app.utils.logger import log_info, log_error, log_warning
from app.utils.screenshots import capture_screenshot

class BrowserManager:
    """
    Playwright Chromium Browser Manager — Single Source of Truth for Account Profiles.
    Resolves persistent account profiles to data/accounts/{account_id}/user_data/.
    Enforces profile lock protection, desktop interface, and state-resilient navigation.
    """
    def __init__(
        self,
        account_id: str = "test_account_01",
        debug_mode: bool = DEFAULT_DEBUG_MODE,
        headless: bool = DEFAULT_HEADLESS,
        window_width: int = DEFAULT_WINDOW_WIDTH,
        window_height: int = DEFAULT_WINDOW_HEIGHT,
        slow_mo: int = DEFAULT_SLOW_MO,
    ):
        self.account_id = account_id
        self.debug_mode = debug_mode
        self.headless = headless if not debug_mode else False  # Force visible when debug_mode ON
        self.window_width = window_width
        self.window_height = window_height
        self.slow_mo = slow_mo if debug_mode else 0

        self.playwright: Playwright = None
        self.context: BrowserContext = None
        self.page: Page = None

        # SINGLE SOURCE OF TRUTH: Account Profile Directory Resolution
        self.profile_dir = (ACCOUNTS_DIR / self.account_id / "user_data").resolve()
        self.profile_dir.mkdir(parents=True, exist_ok=True)

    def print_profile_diagnostic(self):
        """Prints account profile configuration for diagnostic audit."""
        log_info(f"[BROWSER PROFILE] Account ID: {self.account_id}", tag="BROWSER")
        log_info(f"[BROWSER PROFILE] User Data Directory: {self.profile_dir}", tag="BROWSER")
        log_info(f"[BROWSER PROFILE] Persistent: TRUE", tag="BROWSER")
        log_info(f"[BROWSER PROFILE] Headless: {self.headless}", tag="BROWSER")

    def launch(self) -> Page:
        """
        Launches desktop Chromium using account-isolated persistent context.
        """
        self.print_profile_diagnostic()

        try:
            if self.playwright is None:
                self.playwright = sync_playwright().start()

            args = [
                f"--window-size={self.window_width},{self.window_height}",
                "--window-position=100,100",
                "--disable-notifications",
                "--no-sandbox",
            ]

            from app.automation.browser_factory import BrowserFactory
            exec_path, channel = BrowserFactory.get_system_browser()

            launch_kwargs = {
                "user_data_dir": str(self.profile_dir),
                "headless": self.headless,
                "slow_mo": self.slow_mo,
                "args": args,
                "viewport": DEFAULT_DESKTOP_VIEWPORT,
                "is_mobile": False,
                "has_touch": False,
                "user_agent": DEFAULT_DESKTOP_USER_AGENT,
                "accept_downloads": True,
            }
            if exec_path:
                launch_kwargs["executable_path"] = exec_path
            elif channel:
                launch_kwargs["channel"] = channel

            try:
                self.context = self.playwright.chromium.launch_persistent_context(**launch_kwargs)
            except Exception as primary_err:
                log_warning(f"Primary launch failed: {primary_err}. Falling back to Microsoft Edge...", tag="BROWSER")
                launch_kwargs.pop("executable_path", None)
                launch_kwargs["channel"] = "msedge"
                try:
                    self.context = self.playwright.chromium.launch_persistent_context(**launch_kwargs)
                except Exception as edge_err:
                    log_warning(f"Edge launch failed: {edge_err}. Trying Chrome...", tag="BROWSER")
                    launch_kwargs["channel"] = "chrome"
                    self.context = self.playwright.chromium.launch_persistent_context(**launch_kwargs)

            context_created = self.context is not None
            log_info(f"[BROWSER DEBUG] context created={context_created}", tag="BROWSER")

            if self.context.pages:
                self.page = self.context.pages[0]
            else:
                self.page = self.context.new_page()

            page_created = self.page is not None
            log_info(f"[BROWSER DEBUG] page created={page_created}", tag="BROWSER")

            # Verify connection status
            is_connected = False
            if self.context.browser:
                is_connected = self.context.browser.is_connected()
            else:
                is_connected = context_created and page_created

            log_info(f"[BROWSER DEBUG] browser connected={is_connected}", tag="BROWSER")

            if not is_connected or not page_created:
                raise RuntimeError("Browser instance was not properly connected or initialized.")

            log_info(f"[BROWSER DEBUG] page URL={self.page.url}", tag="BROWSER")
            log_info(f"[SESSION] Persistent browser profile loaded: {self.profile_dir}", tag="BROWSER")
            return self.page

        except Exception as e:
            err_msg = str(e)
            if "ProcessSingleton" in err_msg or "profile is already in use" in err_msg.lower():
                log_error("[BROWSER ERROR] Account profile is already in use.", tag="BROWSER")
                log_error(f"[BROWSER ERROR] Account: {self.account_id}", tag="BROWSER")
                log_error(f"[BROWSER ERROR] Profile: {self.profile_dir}", tag="BROWSER")
                log_error("[BROWSER ERROR] Close the existing browser before retrying.", tag="BROWSER")
            else:
                log_error("[BROWSER ERROR] Visible Chromium window could not be created.", tag="BROWSER")
                log_error(f"Traceback:\n{traceback.format_exc()}", tag="BROWSER")

            self.close()
            raise e

    def navigate(self, url: str = FB_DESKTOP_URL) -> bool:
        """
        Navigates to URL using state-resilient navigation.
        Does not treat domcontentloaded timeout as a hard failure if the browser navigated.
        """
        if not self.page:
            raise RuntimeError("Browser is not launched.")

        log_info("[BROWSER] Navigation started", tag="BROWSER")
        log_info(f"Navigating to {url}...", tag="BROWSER")

        try:
            self.page.goto(url, wait_until="commit", timeout=15000)
            try:
                self.page.wait_for_load_state("domcontentloaded", timeout=10000)
            except PlaywrightTimeoutError:
                log_warning("[BROWSER] Navigation event timeout - inspecting current browser state", tag="BROWSER")
                log_info(f"[BROWSER] Current URL: {self.page.url}", tag="BROWSER")
                try:
                    log_info(f"[BROWSER] Current title: {self.page.title()}", tag="BROWSER")
                except Exception:
                    pass
            return True
        except Exception as e:
            log_warning(f"[BROWSER] Soft navigation attempt noticed: {str(e)}", tag="BROWSER")
            log_warning("[BROWSER] Navigation event timeout - inspecting current browser state", tag="BROWSER")
            try:
                log_info(f"[BROWSER] Current URL: {self.page.url}", tag="BROWSER")
                log_info(f"[BROWSER] Current title: {self.page.title()}", tag="BROWSER")
            except Exception:
                pass
            return True

    def wait_for_facebook_ready(self, timeout_seconds: int = 30) -> bool:
        """
        State-based Facebook UI readiness helper.
        Verifies that actual Facebook UI (login or authenticated) is rendered.
        Rejects Chromium 'Restore pages' screen or blank chrome:// pages.
        """
        if not self.page:
            log_error("[BROWSER ERROR] Page is not launched", tag="BROWSER")
            return False

        log_info("[BROWSER] Facebook UI readiness check...", tag="BROWSER")
        start_time = time.time()

        readiness_selectors = [
            # Unauthenticated UI
            "input#email",
            "input#pass",
            "button[name='login']",
            "form#login_form",
            "[data-testid='royal_login_form']",
            # Authenticated UI
            "[aria-label='Your profile']",
            "[aria-label='Account Controls and Settings']",
            "input[placeholder*='Search Facebook']",
            "div[role='banner']",
            "div[role='navigation']",
            "a[href*='/me/']",
            # 2FA / Security Checkpoint UI
            "input[name='approvals_code']",
            "[data-testid='checkpoint']",
        ]

        while time.time() - start_time < timeout_seconds:
            try:
                current_url = self.page.url.lower()

                # Handle Chrome startup restore pages state explicitly
                if "restore-pages" in current_url or "chrome://" in current_url:
                    log_info("[BROWSER] Restore Pages screen detected", tag="BROWSER")
                    log_info("[BROWSER] Waiting for Facebook UI instead of inspecting restore screen", tag="BROWSER")
                    self.page.wait_for_timeout(1000)
                    continue

                # Must be on facebook.com domain (not chrome:// or blank)
                if "facebook.com" in current_url:
                    for selector in readiness_selectors:
                        elem = self.page.query_selector(selector)
                        if elem and elem.is_visible():
                            try:
                                title = self.page.title()
                            except Exception:
                                title = "Facebook"
                            log_info(f"[BROWSER] Current URL: {self.page.url}", tag="BROWSER")
                            log_info(f"[BROWSER] Current title: {title}", tag="BROWSER")
                            log_info("[BROWSER] Facebook UI ready", tag="BROWSER")
                            return True

                self.page.wait_for_timeout(1000)
            except PlaywrightTimeoutError:
                pass
            except Exception as e:
                err_msg = str(e).lower()
                if "navigation" in err_msg or "destroyed" in err_msg:
                    self.page.wait_for_timeout(1000)
                else:
                    break

        # Readiness Timeout / Failure
        log_error("[BROWSER ERROR] Facebook UI did not become ready", tag="BROWSER")
        try:
            log_error(f"[BROWSER ERROR] Final URL: {self.page.url}", tag="BROWSER")
            log_error(f"[BROWSER ERROR] Final title: {self.page.title()}", tag="BROWSER")
        except Exception:
            pass

        self.capture_error(name_prefix="facebook_ui_not_ready")
        return False

    def capture_error(self, name_prefix="browser_error"):
        if self.context:
            return capture_screenshot(self.context, name_prefix=name_prefix)
        return None

    def close(self):
        log_info("Closing browser session...", tag="BROWSER")
        try:
            if self.context:
                self.context.close()
                self.context = None
            if self.playwright:
                self.playwright.stop()
                self.playwright = None
            self.page = None
            log_info("Browser session closed cleanly.", tag="BROWSER")
        except Exception as e:
            log_warning(f"Error during browser close: {str(e)}", tag="BROWSER")
