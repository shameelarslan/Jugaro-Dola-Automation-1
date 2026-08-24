from typing import Tuple, Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from app.utils.logger import log_info, log_error, log_warning
from app.utils.screenshots import capture_screenshot
from app.automation.guards import check_creator_studio_or_waitlist_guard

def normalize_name(name: str) -> str:
    """Normalizes identity/page strings for strict exact matching."""
    return name.strip().lower()

def clean_name(raw: str) -> str:
    """Removes common Facebook UI prefixes/suffixes."""
    c = raw.strip()
    for prefix in ["profile picture for", "picture for", "switch to", "account controls for", "account:"]:
        if c.lower().startswith(prefix):
            c = c[len(prefix):].strip()
    for suffix in ["'s timeline", "'s profile", "'s account"]:
        if c.lower().endswith(suffix):
            c = c[:-len(suffix)].strip()
    return c

def get_original_switcher_container(page: Page):
    """
    Identifies the active top profile switcher container that holds entries like
    'John Dee', 'Create Page', or 'See all Pages'.
    """
    try:
        dialogs_and_menus = page.query_selector_all("div[role='menu'], div[role='dialog'], [role='menu']")
        for container in dialogs_and_menus:
            if container.is_visible():
                text = (container.inner_text() or "").lower()
                if "see all pages" in text or ("john dee" in text and "create page" in text) or ("清浅huang" in text and "create page" in text):
                    return container
        return None
    except Exception:
        return None

def get_new_pages_view_container(page: Page, original_container=None):
    """
    Finds the NEW Pages view container rendered after clicking 'See all Pages'.
    Must NOT be the original switcher container.
    """
    try:
        containers = page.query_selector_all("div[role='dialog'], div[role='menu'], div[role='main']")
        for container in containers:
            if container.is_visible() and container != original_container:
                text = (container.inner_text() or "").lower()
                if "create page" not in text and ("pages" in text or "your pages" in text or "manage" in text):
                    return container
        return None
    except Exception:
        return None

def log_before_click_diagnostic(page: Page, see_all_elem, container_elem):
    """Logs BEFORE CLICK state, URL, container snippet, element info, and captures screenshot."""
    log_info("[PAGE SWITCH DIAGNOSTIC] === BEFORE CLICK DIAGNOSTIC ===", tag="DIAGNOSTIC")
    try:
        log_info(f"[BEFORE CLICK] URL: '{page.url}'", tag="DIAGNOSTIC")
        if container_elem:
            c_tag = container_elem.evaluate("el => el.tagName")
            c_role = container_elem.get_attribute("role") or ""
            c_text_snippet = (container_elem.inner_text() or "")[:200].replace("\n", " ")
            log_info(f"[BEFORE CLICK] Original Switcher Container: Tag='{c_tag}' | Role='{c_role}' | Text Snippet='{c_text_snippet}'", tag="DIAGNOSTIC")

        if see_all_elem:
            e_tag = see_all_elem.evaluate("el => el.tagName")
            e_role = see_all_elem.get_attribute("role") or ""
            e_aria = see_all_elem.get_attribute("aria-label") or ""
            e_text = (see_all_elem.inner_text() or "").strip()
            bbox = see_all_elem.bounding_box()
            log_info(f"[BEFORE CLICK] See all Pages Element: Tag='{e_tag}' | Role='{e_role}' | Aria='{e_aria}' | Text='{e_text}' | BBox={bbox}", tag="DIAGNOSTIC")
    except Exception as e:
        log_warning(f"[BEFORE CLICK] Diagnostic error: {e}", tag="DIAGNOSTIC")
    capture_screenshot(page, name_prefix="before_see_all_pages_click")
    log_info("[PAGE SWITCH DIAGNOSTIC] === END BEFORE CLICK DIAGNOSTIC ===", tag="DIAGNOSTIC")

def log_after_click_diagnostic(page: Page, original_container_visible: bool, new_container_elem):
    """Logs AFTER CLICK state, URL, container visibility, headings, buttons, text snippet, and captures screenshot."""
    log_info("[PAGE SWITCH DIAGNOSTIC] === AFTER CLICK DIAGNOSTIC ===", tag="DIAGNOSTIC")
    try:
        log_info(f"[AFTER CLICK] URL: '{page.url}'", tag="DIAGNOSTIC")
        log_info(f"[AFTER CLICK] Original Switcher Container Still Visible: {original_container_visible}", tag="DIAGNOSTIC")

        if new_container_elem:
            n_tag = new_container_elem.evaluate("el => el.tagName")
            n_role = new_container_elem.get_attribute("role") or ""

            headings = new_container_elem.query_selector_all("h1, h2, h3, span[role='heading']")
            h_texts = [h.inner_text().strip() for h in headings if h.is_visible() and h.inner_text().strip()]

            buttons = new_container_elem.query_selector_all("button, [role='button']")
            b_texts = [b.inner_text().strip() for b in buttons if b.is_visible() and b.inner_text().strip()]

            first_1000_chars = (new_container_elem.inner_text() or "")[:1000].replace("\n", " ")

            log_info(f"[AFTER CLICK] New Container: Tag='{n_tag}' | Role='{n_role}'", tag="DIAGNOSTIC")
            log_info(f"[AFTER CLICK] New Container Headings: {h_texts[:5]}", tag="DIAGNOSTIC")
            log_info(f"[AFTER CLICK] New Container Buttons: {b_texts[:10]}", tag="DIAGNOSTIC")
            log_info(f"[AFTER CLICK] New Container Text Snippet (1000 chars): {first_1000_chars}", tag="DIAGNOSTIC")
        else:
            log_info("[AFTER CLICK] New Container: NONE DETECTED", tag="DIAGNOSTIC")
    except Exception as e:
        log_warning(f"[AFTER CLICK] Diagnostic error: {e}", tag="DIAGNOSTIC")
    capture_screenshot(page, name_prefix="after_see_all_pages_click")
    log_info("[PAGE SWITCH DIAGNOSTIC] === END AFTER CLICK DIAGNOSTIC ===", tag="DIAGNOSTIC")

class PageSwitcher:
    """
    DOM-Based Facebook Page Switcher — Scoped Pages View Container Flow.
    Verifies genuine Pages view transition by checking dismissal of original profile container.
    Performs STRICT SCOPED EXACT NORMALIZED MATCHING inside new Pages container ONLY.
    Never uses broad document-wide searches or interchangeable 'See all profiles' selectors.
    """
    def __init__(self, page: Page):
        self.page = page

    def switch_to_page(self, target_page_name: str) -> bool:
        """
        Executes Page Switching using scoped Pages view container.
        """
        target_norm = normalize_name(target_page_name)
        log_info(f"[TARGET PAGE] {target_page_name} (Normalized: '{target_norm}')", tag="TARGET_PAGE")
        log_info("[PAGE SWITCH] Searching for account/profile control...", tag="PAGE_SWITCH")

        # Step 1: Candidate Discovery for Account / Profile Control
        profile_selectors = [
            "[aria-label='Your profile']",
            "[aria-label='Account Controls and Settings']",
            "div[role='navigation'] [aria-label*='Profile']",
            "div[role='banner'] [aria-label*='Profile']",
        ]

        profile_control = None
        for selector in profile_selectors:
            try:
                elem = self.page.query_selector(selector)
                if elem and elem.is_visible():
                    aria = elem.get_attribute("aria-label") or ""
                    text = elem.inner_text().strip()
                    log_info(f"[PAGE SWITCH] Account control candidate found: selector='{selector}', aria='{aria}', text='{text}'", tag="PAGE_SWITCH")
                    log_info("[PAGE SWITCH] Visibility: TRUE", tag="PAGE_SWITCH")
                    log_info("[PAGE SWITCH] Account control verified", tag="PAGE_SWITCH")
                    profile_control = elem
                    break
            except Exception:
                pass

        if not profile_control:
            log_error("[PAGE SWITCH] SAFE_STOP", tag="PAGE_SWITCH")
            log_error("[PAGE SWITCH] Reason: Account/profile switcher control not found in DOM.", tag="PAGE_SWITCH")
            return False

        # Open Top Profile Menu
        log_info("[PAGE SWITCH] Opening profile switcher menu...", tag="PAGE_SWITCH")
        try:
            profile_control.click()
            self.page.wait_for_timeout(1500)
        except Exception as e:
            err_str = str(e).lower()
            if "destroyed" in err_str or "navigation" in err_str:
                log_info("[PAGE VERIFY] Facebook navigation transition detected", tag="PAGE_VERIFY")
                self.page.wait_for_timeout(3000)
            else:
                log_error("[PAGE SWITCH] SAFE_STOP", tag="PAGE_SWITCH")
                log_error(f"[PAGE SWITCH] Reason: Error clicking profile control: {str(e)}", tag="PAGE_SWITCH")
                return False

        log_info("[PAGE SWITCH] Profile switcher menu opened", tag="PAGE_SWITCH")

        # Identify Original Profile Switcher Container
        original_container = get_original_switcher_container(self.page)

        # Step 2: Search and Click EXACT 'See all Pages' Control
        log_info("[PAGE SWITCH] Searching for exact 'See all Pages' entry...", tag="PAGE_SWITCH")

        # STRICTLY NO 'See all profiles' SELECTORS
        see_all_pages_selectors = [
            "span:has-text('See all Pages')",
            "span:has-text('See all pages')",
            "[aria-label='See all Pages']",
            "[aria-label='See all pages']",
            "div[role='button']:has-text('See all Pages')",
            "div[role='button']:has-text('See all pages')",
            "a:has-text('See all Pages')",
            "a:has-text('See all pages')",
        ]

        see_all_elem = None
        for see_sel in see_all_pages_selectors:
            try:
                elems = self.page.query_selector_all(see_sel)
                for el in elems:
                    if el.is_visible():
                        see_all_elem = el
                        break
                if see_all_elem:
                    break
            except Exception:
                pass

        if not see_all_elem:
            log_error("[PAGE SWITCH] PAGES_VIEW_NOT_OPENED", tag="PAGE_SWITCH")
            log_error("[PAGE SWITCH] SAFE_STOP", tag="PAGE_SWITCH")
            log_error("[PAGE SWITCH] Reason: Could not locate exact 'See all Pages' control in profile menu.", tag="PAGE_SWITCH")
            return False

        # Resolve interactive parent container
        parent_handle = see_all_elem.evaluate_handle("el => el.closest('[role=\"button\"], [role=\"menuitem\"], button, a') || el")
        parent_elem = parent_handle.as_element() or see_all_elem

        # Log BEFORE CLICK Diagnostic
        log_before_click_diagnostic(self.page, see_all_elem, original_container)

        # Click interactive parent container
        try:
            log_info("[PAGE SWITCH] Clicking interactive parent container of exact 'See all Pages'...", tag="PAGE_SWITCH")
            parent_elem.click()
            self.page.wait_for_timeout(2500)
        except Exception as e:
            log_warning(f"[PAGE SWITCH] Click error on 'See all Pages': {str(e)}", tag="PAGE_SWITCH")

        # Check AFTER CLICK Container State
        original_visible = False
        if original_container:
            try:
                original_visible = original_container.is_visible()
            except Exception:
                original_visible = False

        new_container = get_new_pages_view_container(self.page, original_container=original_container)

        # Log AFTER CLICK Diagnostic
        log_after_click_diagnostic(self.page, original_visible, new_container)

        # Transition Verification: MUST FAIL if original container is still visible OR if new container is missing
        if original_visible or not new_container:
            log_error("[PAGE SWITCH] PAGES_VIEW_NOT_OPENED", tag="PAGE_SWITCH")
            log_error("[PAGE SWITCH] SAFE_STOP", tag="PAGE_SWITCH")
            log_error("[PAGE SWITCH] Reason: Pages view transition failed — original switcher menu remains visible or new Pages container missing.", tag="PAGE_SWITCH")
            return False

        log_info("[PAGE SWITCH] Pages view transition VERIFIED! Original profile switcher dismissed and new Pages container detected.", tag="PAGE_SWITCH")

        # Step 3: Search for 'Huang' ONLY INSIDE THE VERIFIED NEW PAGES CONTAINER
        log_info(f"[PAGE SWITCH] Searching inside new Pages container for target: '{target_page_name}' (STRICT SCOPED MATCH: normalize(found) == '{target_norm}')", tag="PAGE_SWITCH")

        visible_page_names = []
        target_candidate = None
        selected_page_name = ""

        invalid_names = ["john dee", "清浅huang", "amazing world", "create page", "see all pages", "see all profiles"]

        elems = new_container.query_selector_all("div[role='button'], [role='menuitem'], a, button, span")
        for elem in elems:
            if elem.is_visible():
                raw_txt = elem.inner_text().strip()
                cleaned_txt = clean_name(raw_txt)
                norm_cleaned = normalize_name(cleaned_txt)

                if norm_cleaned in invalid_names:
                    continue

                if cleaned_txt and cleaned_txt not in visible_page_names and len(cleaned_txt) < 50:
                    visible_page_names.append(cleaned_txt)

                # STRICT EXACT NORMALIZED MATCHING (STRICTLY INSIDE NEW CONTAINER ONLY!)
                if norm_cleaned == target_norm:
                    target_candidate = elem
                    selected_page_name = cleaned_txt
                    log_info(f"[PAGE SWITCH] Scoped target match found in new container: raw='{raw_txt}' | cleaned='{cleaned_txt}'", tag="PAGE_SWITCH")
                    break

        log_info(f"[PAGE SWITCH] All visible Page names inside new container ({len(visible_page_names)} found): {visible_page_names[:10]}", tag="PAGE_SWITCH")

        # Step 4: Handle TARGET_PAGE_NOT_FOUND Safety Stop
        if not target_candidate:
            log_error("[PAGE SWITCH] TARGET_PAGE_NOT_FOUND_IN_ALL_PAGES", tag="PAGE_SWITCH")
            log_error("[PAGE SWITCH] SAFE_STOP", tag="PAGE_SWITCH")
            log_error(f"[PAGE SWITCH] Reason: Target Page '{target_page_name}' was not found inside the new Pages view container.", tag="PAGE_SWITCH")
            return False

        # Step 5: Click Exact Target Page Candidate Container
        log_info(f"[PAGE SWITCH] Selected Page name: '{selected_page_name}'", tag="PAGE_SWITCH")
        log_info(f"[PAGE SWITCH] Clicking target Page '{target_page_name}'...", tag="PAGE_SWITCH")

        try:
            target_candidate.click()
            self.page.wait_for_timeout(2500)
        except Exception as e:
            err_str = str(e).lower()
            if "destroyed" in err_str or "navigation" in err_str:
                log_info("[PAGE VERIFY] Facebook navigation transition detected", tag="PAGE_VERIFY")
                self.page.wait_for_timeout(3000)
            else:
                log_error("[PAGE SWITCH] SAFE_STOP", tag="PAGE_SWITCH")
                log_error(f"[PAGE SWITCH] Reason: Error clicking target Page candidate: {str(e)}", tag="PAGE_SWITCH")
                return False

        # Step 6: Handle Switch Confirmation Dialog if Facebook displays one
        try:
            dialogs = self.page.query_selector_all("div[role='dialog']")
            active_dialog = None
            for dlg in dialogs:
                if dlg.is_visible() and dlg != original_container and dlg != new_container:
                    active_dialog = dlg
                    break

            if active_dialog:
                log_info("[PAGE SWITCH] Switch confirmation dialog detected", tag="PAGE_SWITCH")
                buttons = active_dialog.query_selector_all("button, [role='button']")
                switch_button = None
                valid_switch_keywords = ["switch", "switch into", "switch to"]
                invalid_keywords = ["cancel", "close", "back", "create", "scheduling", "creator studio"]

                for btn in buttons:
                    if not btn.is_visible():
                        continue
                    btn_text = btn.inner_text().strip().lower()
                    btn_aria = (btn.get_attribute("aria-label") or "").strip().lower()
                    combined = f"{btn_text} {btn_aria}"

                    if any(inv in combined for inv in invalid_keywords):
                        continue

                    if any(valid in combined for valid in valid_switch_keywords):
                        switch_button = btn
                        log_info(f"[PAGE SWITCH] Verified SWITCH button: '{btn.inner_text().strip()}'", tag="PAGE_SWITCH")
                        break

                if switch_button:
                    log_info("[PAGE SWITCH] Clicking confirmation SWITCH button...", tag="PAGE_SWITCH")
                    try:
                        switch_button.click()
                        self.page.wait_for_timeout(3000)
                    except Exception as e:
                        err_str = str(e).lower()
                        if "destroyed" in err_str or "navigation" in err_str:
                            log_info("[PAGE VERIFY] Facebook navigation transition detected", tag="PAGE_VERIFY")
                            self.page.wait_for_timeout(3000)
        except Exception as e:
            err_str = str(e).lower()
            if "destroyed" in err_str or "navigation" in err_str:
                log_info("[PAGE VERIFY] Facebook navigation transition detected", tag="PAGE_VERIFY")
                self.page.wait_for_timeout(3000)

        # Step 7: Wait for Identity Transition
        log_info("[PAGE VERIFY] Waiting for Facebook identity transition...", tag="PAGE_VERIFY")

        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=15000)
            self.page.wait_for_timeout(3000)
        except PlaywrightTimeoutError:
            log_warning("[PAGE VERIFY] Soft load state timeout during transition, checking DOM identity...", tag="PAGE_VERIFY")

        # Check Guard
        if check_creator_studio_or_waitlist_guard(self.page):
            log_error("[PAGE SWITCH] SAFE_STOP", tag="PAGE_SWITCH")
            log_error("[PAGE SWITCH] Reason: Creator Studio / Waitlist detected after switch attempt.", tag="PAGE_SWITCH")
            return False

        return True
