"""
State Machine Engine for FB AutoViral SaaS Pro.
Enforces explicit state transitions, DOM-based verification, strict current page pre-check, and failure safety.
"""

import traceback
from enum import Enum
from app.browser.browser_manager import BrowserManager
from app.browser.session_manager import SessionManager, SessionStatus
from app.facebook.page_switcher import PageSwitcher
from app.facebook.identity_verifier import IdentityVerifier, IdentityType
from app.automation.guards import check_creator_studio_or_waitlist_guard
from app.utils.logger import log_info, log_error, log_warning

class AutomationState(Enum):
    ACCOUNT_READY = "ACCOUNT_READY"
    SESSION_VERIFY = "SESSION_VERIFY"
    CURRENT_PAGE_CONTEXT_CHECK = "CURRENT_PAGE_CONTEXT_CHECK"
    PROFILE_CONTROL_DISCOVERY = "PROFILE_CONTROL_DISCOVERY"
    PROFILE_SWITCHER_OPEN = "PROFILE_SWITCHER_OPEN"
    TARGET_PAGE_DISCOVERY = "TARGET_PAGE_DISCOVERY"
    TARGET_PAGE_SELECTION = "TARGET_PAGE_SELECTION"
    SWITCH_CONFIRMATION = "SWITCH_CONFIRMATION"
    IDENTITY_TRANSITION = "IDENTITY_TRANSITION"
    IDENTITY_VERIFICATION = "IDENTITY_VERIFICATION"
    PAGE_CONTEXT_VERIFIED = "PAGE_CONTEXT_VERIFIED"
    FAILED = "FAILED"

class StateMachine:
    """
    Core Automation State Machine.
    Coordinates browser launch, session verification, strict current context pre-check,
    Page switching, and identity verification.
    """
    def __init__(self, account_id: str = "test_account_01", target_page: str = "Huang"):
        self.account_id = account_id
        self.target_page = target_page
        self.current_state = AutomationState.ACCOUNT_READY
        self.bm: BrowserManager = None

    def transition_to(self, new_state: AutomationState, message: str = ""):
        self.current_state = new_state
        msg = f"[STATE MACHINE] Transitioned to {new_state.value}"
        if message:
            msg += f" — {message}"
        log_info(msg, tag="STATE")

    def run_page_switch_workflow(self) -> bool:
        """
        Executes verified Page Switching state machine pipeline up to PAGE_CONTEXT_VERIFIED.
        Includes Strict Current Active Page Pre-Check with Page-vs-Personal discrimination.
        """
        log_info(f"[ACCOUNT] {self.account_id}", tag="ACCOUNT")
        log_info(f"[TARGET PAGE] {self.target_page}", tag="TARGET_PAGE")
        log_info("[AUTOMATION] Beginning Page Switch workflow...", tag="AUTOMATION")

        self.transition_to(AutomationState.ACCOUNT_READY, f"Account: {self.account_id}")

        try:
            # 1. SESSION_VERIFY State
            self.transition_to(AutomationState.SESSION_VERIFY)
            self.bm = BrowserManager(
                account_id=self.account_id,
                debug_mode=True,
                headless=False,
                window_width=500,
                window_height=600,
            )
            page = self.bm.launch()
            sm = SessionManager(self.bm)

            self.bm.navigate("https://www.facebook.com/")
            if not self.bm.wait_for_facebook_ready(timeout_seconds=30):
                self.transition_to(AutomationState.FAILED, "Facebook UI did not become ready")
                return False

            session_status = sm.check_session(page)
            if session_status != SessionStatus.LOGGED_IN:
                log_warning("[AUTOMATION] Session not LIVE. Waiting for manual login...", tag="AUTOMATION")
                if not sm.wait_for_manual_login(page):
                    self.transition_to(AutomationState.FAILED, "Session is not LIVE")
                    return False

            log_info("[AUTOMATION] Account session verified", tag="AUTOMATION")
            log_info("[AUTOMATION] Facebook UI ready", tag="AUTOMATION")

            # Check Guard before context check
            if check_creator_studio_or_waitlist_guard(page):
                log_error("[PAGE SWITCH] SAFE_STOP", tag="PAGE_SWITCH")
                log_error("[PAGE SWITCH] Reason: Creator Studio / Waitlist detected", tag="PAGE_SWITCH")
                self.transition_to(AutomationState.FAILED, "Creator Studio / Waitlist guard triggered")
                return False

            # 2. CURRENT_PAGE_CONTEXT_CHECK State
            self.transition_to(AutomationState.CURRENT_PAGE_CONTEXT_CHECK)
            log_info("[PAGE CHECK] Checking current active Page...", tag="PAGE_CHECK")

            verifier = IdentityVerifier(page)
            already_active, current_identity, id_type, initial_signals = verifier.verify_active_identity(self.target_page)

            # CASE A — TARGET_ALREADY_ACTIVE
            if already_active:
                log_info(f"[PAGE CHECK] Identity type: {id_type.value}", tag="PAGE_CHECK")
                log_info(f"[PAGE CHECK] Active identity: {current_identity}", tag="PAGE_CHECK")
                log_info(f"[PAGE CHECK] Target Page: {self.target_page}", tag="PAGE_CHECK")
                log_info("[PAGE CHECK] TARGET_ALREADY_ACTIVE", tag="PAGE_CHECK")
                log_info(f"[PAGE CHECK] Target Page '{self.target_page}' is already active", tag="PAGE_CHECK")
                log_info("[PAGE VERIFY] SUCCESS", tag="PAGE_VERIFY")
                log_info(f"[AUTOMATION] Target Page context verified: {self.target_page}", tag="AUTOMATION")
                self.transition_to(AutomationState.PAGE_CONTEXT_VERIFIED, f"Target Page '{self.target_page}' was already active.")
                return True

            # CASE C — IDENTITY_AMBIGUOUS
            if id_type == IdentityType.IDENTITY_AMBIGUOUS:
                log_warning(f"[PAGE CHECK] Identity type: {id_type.value}", tag="PAGE_CHECK")
                log_warning(f"[PAGE CHECK] Active identity: {current_identity}", tag="PAGE_CHECK")
                log_warning(f"[PAGE CHECK] Target Page: {self.target_page}", tag="PAGE_CHECK")
                log_error("[PAGE SWITCH] SAFE_STOP", tag="PAGE_SWITCH")
                log_error("[PAGE SWITCH] Reason: Active identity could not be determined with strong confidence.", tag="PAGE_SWITCH")
                self.bm.capture_error(name_prefix="identity_ambiguous_precheck")
                self.transition_to(AutomationState.FAILED, "Identity ambiguous during pre-check")
                return False

            # CASE B — TARGET_NOT_ACTIVE (PERSONAL_PROFILE or DIFFERENT_PAGE)
            log_info(f"[PAGE CHECK] Identity type: {id_type.value}", tag="PAGE_CHECK")
            log_info(f"[PAGE CHECK] Active identity: {current_identity}", tag="PAGE_CHECK")
            log_info(f"[PAGE CHECK] Target Page: {self.target_page}", tag="PAGE_CHECK")
            log_info("[PAGE CHECK] TARGET_NOT_ACTIVE", tag="PAGE_CHECK")
            log_info("[PAGE SWITCH] PAGE_SWITCH_REQUIRED", tag="PAGE_SWITCH")

            # Proceed with Page Switching Workflow
            self.transition_to(AutomationState.PROFILE_CONTROL_DISCOVERY)
            switcher = PageSwitcher(page)

            self.transition_to(AutomationState.PROFILE_SWITCHER_OPEN)
            self.transition_to(AutomationState.TARGET_PAGE_DISCOVERY)
            self.transition_to(AutomationState.TARGET_PAGE_SELECTION)

            switch_success = switcher.switch_to_page(self.target_page)
            if not switch_success:
                log_error("[PAGE SWITCH] SAFE_STOP", tag="PAGE_SWITCH")
                log_error(f"[PAGE SWITCH] Reason: Could not complete switch to target Page '{self.target_page}'", tag="PAGE_SWITCH")
                self.bm.capture_error(name_prefix="page_switch_failed")
                self.transition_to(AutomationState.FAILED, "Page switch execution failed")
                return False

            # 3. IDENTITY_VERIFICATION State
            self.transition_to(AutomationState.IDENTITY_VERIFICATION)
            log_info("[PAGE VERIFY] Inspecting active identity...", tag="PAGE_VERIFY")

            is_verified, actual_identity, post_id_type, signals = verifier.verify_active_identity(self.target_page)

            if is_verified:
                log_info(f"[PAGE VERIFY] Expected: {self.target_page}", tag="PAGE_VERIFY")
                log_info(f"[PAGE VERIFY] Actual: {actual_identity}", tag="PAGE_VERIFY")
                log_info(f"[PAGE VERIFY] Identity evidence: {signals}", tag="PAGE_VERIFY")
                log_info("[PAGE VERIFY] SUCCESS", tag="PAGE_VERIFY")
                log_info(f"[AUTOMATION] Target Page context verified: {self.target_page}", tag="AUTOMATION")
                self.transition_to(AutomationState.PAGE_CONTEXT_VERIFIED, f"Target Page '{self.target_page}' verified active.")
                return True
            else:
                log_error("[PAGE SWITCH] SAFE_STOP", tag="PAGE_SWITCH")
                log_error(f"[PAGE SWITCH] Reason: Active identity '{actual_identity}' mismatch with expected '{self.target_page}'", tag="PAGE_SWITCH")
                self.bm.capture_error(name_prefix="identity_verification_failed")
                self.transition_to(AutomationState.FAILED, "Identity verification failed")
                return False

        except Exception as e:
            log_error(f"[AUTOMATION ERROR] State machine exception: {str(e)}", tag="AUTOMATION")
            log_error(f"Traceback:\n{traceback.format_exc()}", tag="AUTOMATION")
            if self.bm:
                self.bm.capture_error(name_prefix="state_machine_exception")
            self.transition_to(AutomationState.FAILED, str(e))
            return False
