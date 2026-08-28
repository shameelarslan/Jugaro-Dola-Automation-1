import time
from enum import Enum
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from config import FB_DESKTOP_URL
from app.utils.logger import log_info, log_error, log_warning
from app.utils.screenshots import capture_screenshot

class SessionStatus(Enum):
    LOGIN_REQUIRED = "LOGIN REQUIRED"
    LOGIN_IN_PROGRESS = "LOGIN IN PROGRESS"
    LOGGED_IN = "LIVE"
    SESSION_EXPIRED = "SESSION EXPIRED"
    SESSION_ERROR = "SESSION ERROR"

class SessionManager:
    """
    Robust Facebook Session & Login Persistence Manager.
    Enforces multi-signal DOM inspection, navigation guards, 2FA/checkpoint isolation,
    and consecutive stability verification window before declaring LIVE status.
    """
    def __init__(self, browser_manager):
        self.browser_manager = browser_manager

    def check_session(self, page: Page) -> SessionStatus:
        """
        Navigates to Facebook Desktop and inspects DOM signals to determine session status.
        Does NOT automate credential entry.
        """
        log_info(f"[ACCOUNT] {self.browser_manager.account_id}", tag="ACCOUNT")
        log_info("[SESSION] Browser profile loaded", tag="SESSION")
        log_info("[SESSION] Opening Facebook...", tag="SESSION")

        try:
            page.goto(FB_DESKTOP_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)
        except PlaywrightTimeoutError:
            log_error("[SESSION ERROR] Facebook navigation timed out", tag="SESSION")
            capture_screenshot(page, name_prefix="session_nav_timeout")
            return SessionStatus.SESSION_ERROR
        except Exception as e:
            log_error(f"[SESSION ERROR] Facebook navigation failed: {str(e)}", tag="SESSION")
            capture_screenshot(page, name_prefix="session_nav_failed")
            return SessionStatus.SESSION_ERROR

        status, _ = self.verify_stable_authenticated_state(page, required_checks=2)
        return status

    def inspect_single_snapshot(self, page: Page):
        """
        Performs a single snapshot evaluation of the Facebook page.
        Returns (status, signals_list, error_flag).
        Handles page navigation exceptions cleanly.
        """
        try:
            url = page.url.lower()

            # 1. Check for 2FA / Security Checkpoints / Login Approvals
            challenge_url_keywords = [
                "/checkpoint", "/two_factor", "/challenge", "/confirm",
                "/login/device-based", "/security", "/approval"
            ]
            is_challenge_url = any(keyword in url for keyword in challenge_url_keywords)

            challenge_selectors = [
                "input[name='approvals_code']",
                "button[id*='checkpoint']",
                "[data-testid='checkpoint']",
                "input[placeholder*='code']",
                "form[action*='checkpoint']",
            ]

            challenge_signal = False
            if is_challenge_url:
                challenge_signal = True
            else:
                for selector in challenge_selectors:
                    try:
                        elem = page.query_selector(selector)
                        if elem and elem.is_visible():
                            challenge_signal = True
                            break
                    except Exception:
                        pass

            if challenge_signal:
                log_info("[SESSION] Login verification in progress", tag="SESSION")
                log_info("[SESSION] 2FA / security verification detected", tag="SESSION")
                log_info("[SESSION] Status: LOGIN IN PROGRESS", tag="SESSION")
                return SessionStatus.LOGIN_IN_PROGRESS, [], False

            # 2. Check for Unauthenticated Login Form UI
            unauthenticated_selectors = [
                "input#email",
                "input#pass",
                "button[name='login']",
                "form#login_form",
                "[data-testid='royal_login_form']",
                "a[href*='recover/initiate']",
            ]

            login_form_count = 0
            for selector in unauthenticated_selectors:
                try:
                    if page.query_selector(selector):
                        login_form_count += 1
                except Exception:
                    pass

            if login_form_count >= 1 or "/login" in url or "login.php" in url:
                log_warning("[SESSION] Login required", tag="SESSION")
                return SessionStatus.LOGIN_REQUIRED, [], False

            # 3. Check for Strong Authenticated DOM Signals
            strong_authenticated_selectors = [
                "[aria-label='Your profile']",
                "[aria-label='Account Controls and Settings']",
                "input[placeholder*='Search Facebook']",
                "div[role='banner'] [aria-label*='Search']",
                "a[href*='/me/'][role='link']",
                "div[role='navigation'] [aria-label*='Profile']",
            ]

            detected_signals = []
            for selector in strong_authenticated_selectors:
                try:
                    element = page.query_selector(selector)
                    if element and element.is_visible():
                        detected_signals.append(selector)
                except Exception:
                    pass

            if detected_signals:
                return SessionStatus.LOGGED_IN, detected_signals, False

            # If no explicit login form and no 2FA, but still in transition/loading
            log_info("[SESSION] Login verification in progress", tag="SESSION")
            return SessionStatus.LOGIN_IN_PROGRESS, [], False

        except Exception as e:
            err_msg = str(e).lower()
            if "execution context was destroyed" in err_msg or "navigation" in err_msg or "target closed" in err_msg:
                log_info("[SESSION] Facebook navigation detected", tag="SESSION")
                log_info("[SESSION] Authentication state temporarily unstable", tag="SESSION")
                log_info("[SESSION] Rechecking...", tag="SESSION")
                return SessionStatus.LOGIN_IN_PROGRESS, [], True
            else:
                log_error(f"[SESSION ERROR] Error during snapshot check: {str(e)}", tag="SESSION")
                return SessionStatus.SESSION_ERROR, [], True

    def verify_stable_authenticated_state(self, page: Page, required_checks=3, check_interval=1.5):
        """
        Enforces a consecutive stability verification window before returning LIVE.
        Requires 'required_checks' consecutive positive checks spaced 'check_interval' seconds apart.
        """
        consecutive_matches = 0
        last_signals = []

        log_info("[SESSION] Authenticated state candidate evaluation starting...", tag="SESSION")

        for check_num in range(1, required_checks + 1):
            status, signals, is_navigating = self.inspect_single_snapshot(page)

            if is_navigating or status != SessionStatus.LOGGED_IN:
                log_info(f"[SESSION] Stability check {check_num} failed or in progress ({status.value}). Resetting candidate state.", tag="SESSION")
                return SessionStatus.LOGIN_IN_PROGRESS, []

            if check_num == 1:
                log_info("[SESSION] Authenticated state candidate detected", tag="SESSION")

            log_info(f"[SESSION] Verifying authenticated state stability (Check {check_num} of {required_checks})...", tag="SESSION")
            consecutive_matches += 1
            last_signals = signals

            if check_num < required_checks:
                page.wait_for_timeout(int(check_interval * 1000))

        if consecutive_matches == required_checks:
            log_info("[SESSION] Authenticated state stable", tag="SESSION")
            log_info("[SESSION] Authenticated state verified", tag="SESSION")
            log_info("[SESSION] Status: LIVE", tag="SESSION")
            return SessionStatus.LOGGED_IN, last_signals

        return SessionStatus.LOGIN_IN_PROGRESS, []

    def wait_for_manual_login(self, page: Page, timeout_seconds: int = 600, status_callback=None) -> bool:
        """
        Monitors manual Facebook login flow until authenticated state is stable across multiple checks.
        """
        log_warning("[SESSION] Login required", tag="SESSION")
        log_info("[SESSION] Waiting for manual Facebook login...", tag="SESSION")

        if status_callback:
            status_callback(SessionStatus.LOGIN_IN_PROGRESS)

        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            status, signals, is_navigating = self.inspect_single_snapshot(page)

            if is_navigating:
                page.wait_for_timeout(2000)
                continue

            if status == SessionStatus.LOGGED_IN:
                # Run consecutive stability verification window (3 consecutive checks)
                stable_status, stable_signals = self.verify_stable_authenticated_state(page, required_checks=3, check_interval=1.5)
                if stable_status == SessionStatus.LOGGED_IN:
                    log_info("[SESSION] Manual login detected", tag="SESSION")
                    log_info("[SESSION] Authenticated state verified", tag="SESSION")
                    log_info("[SESSION] Status: LIVE", tag="SESSION")
                    if status_callback:
                        status_callback(SessionStatus.LOGGED_IN)
                    return True

            page.wait_for_timeout(2500)

        log_error("[SESSION ERROR] Manual login timed out", tag="SESSION")
        if status_callback:
            status_callback(SessionStatus.SESSION_EXPIRED)
        return False
