import sys
import time
import traceback
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.browser.browser_manager import BrowserManager
from app.browser.session_manager import SessionManager, SessionStatus
from app.utils.logger import log_info, log_error, log_warning

def test_visible_browser_launch_and_session(timeout_seconds=300):
    """
    Visible Browser Launch Diagnostic & Session Persistence Harness.
    
    1. Launches visible Chromium (headless=False).
    2. Verifies browser connection & context creation.
    3. Navigates to Facebook.
    4. If LOGIN_REQUIRED, prints instructions ONLY after visible browser is verified alive.
    5. Re-tests persistence on clean restart (RUN 2).
    """
    account_id = "test_account_01"
    log_info(f"--- STARTING BROWSER VISIBILITY & SESSION DIAGNOSTIC TEST [ACCOUNT: {account_id}] ---", tag="SESSION_TEST")

    # =========================================================================
    # RUN 1: Visible Browser Launch & Session Check
    # =========================================================================
    log_info("=== RUN 1: Launching Visible Chromium Browser ===", tag="SESSION_TEST")
    bm1 = BrowserManager(
        account_id=account_id,
        debug_mode=True,  # Mandatory visible browser launch
        headless=False,
        window_width=500,
        window_height=600,
        slow_mo=300
    )

    try:
        page1 = bm1.launch()

        # Strict Visibility & Connection Guard
        if not page1 or not bm1.context:
            log_error("[BROWSER ERROR] Visible Chromium window could not be created.", tag="SESSION_TEST")
            return False

        sm1 = SessionManager(bm1)
        status1 = sm1.check_session(page1)

        if status1 == SessionStatus.LOGIN_REQUIRED:
            log_warning("[SESSION] Login required", tag="SESSION")
            log_info("[SESSION] Waiting for manual Facebook login...", tag="SESSION")
            log_info("[SESSION] Please complete login in the visible browser.", tag="SESSION")

            login_success = sm1.wait_for_manual_login(page1, timeout_seconds=timeout_seconds)

            if not login_success:
                log_error("[SESSION_TEST] Manual login was not completed within timeout.", tag="SESSION_TEST")
                bm1.close()
                return False

            time.sleep(4)
            bm1.close()
            log_info("=== RUN 1 Completed: Manual login persisted & browser closed cleanly. ===", tag="SESSION_TEST")

        elif status1 == SessionStatus.LOGGED_IN:
            log_info("[SESSION_TEST] Existing authenticated session detected", tag="SESSION_TEST")
            log_info("[SESSION_TEST] Status: LIVE", tag="SESSION_TEST")
            time.sleep(2)
            bm1.close()
            log_info("=== RUN 1 Completed: Existing session confirmed & browser closed cleanly. ===", tag="SESSION_TEST")
        else:
            log_error(f"[SESSION_TEST] Unexpected status: {status1.value}", tag="SESSION_TEST")
            bm1.close()
            return False

    except Exception as e:
        log_error("[BROWSER ERROR] Visible Chromium window could not be created.", tag="SESSION_TEST")
        log_error(f"Traceback:\n{traceback.format_exc()}", tag="SESSION_TEST")
        if bm1:
            bm1.close()
        return False

    time.sleep(2)

    # =========================================================================
    # RUN 2: Reopen with EXACT SAME Profile & Verify Persistence
    # =========================================================================
    log_info("=== RUN 2: Reopening Browser using the EXACT SAME Profile ===", tag="SESSION_TEST")
    bm2 = BrowserManager(
        account_id=account_id,
        debug_mode=True,
        headless=False,
        window_width=500,
        window_height=600,
        slow_mo=300
    )

    try:
        page2 = bm2.launch()
        sm2 = SessionManager(bm2)
        status2 = sm2.check_session(page2)

        if status2 == SessionStatus.LOGGED_IN:
            log_info("[SESSION_TEST] Existing authenticated session detected", tag="SESSION_TEST")
            log_info("[SESSION_TEST] Status: LIVE", tag="SESSION_TEST")
            log_info("[SESSION_TEST] Persistent login VERIFIED", tag="SESSION_TEST")
            time.sleep(3)
            bm2.close()
            log_info("--- REAL SESSION PERSISTENCE TEST PASSED SUCCESSFULLY ---", tag="SESSION_TEST")
            return True
        else:
            log_error("[SESSION_TEST] Persistent login FAILED", tag="SESSION_TEST")
            log_error(f"[SESSION_TEST] Status on restart: {status2.value}", tag="SESSION_TEST")
            bm2.close()
            return False

    except Exception as e:
        log_error("[BROWSER ERROR] Visible Chromium window could not be created during Run 2.", tag="SESSION_TEST")
        log_error(f"Traceback:\n{traceback.format_exc()}", tag="SESSION_TEST")
        if bm2:
            bm2.close()
        return False

if __name__ == "__main__":
    success = test_visible_browser_launch_and_session()
    sys.exit(0 if success else 1)
