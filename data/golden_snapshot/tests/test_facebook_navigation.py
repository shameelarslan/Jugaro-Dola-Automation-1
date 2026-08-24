import sys
import time
import traceback
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.browser.browser_manager import BrowserManager
from app.browser.session_manager import SessionManager
from app.utils.logger import log_info, log_error, log_warning

def safe_input(prompt_msg):
    try:
        return input(prompt_msg)
    except (EOFError, KeyboardInterrupt):
        print("\n[NAV_TEST] Non-interactive environment detected. Continuing...")
        return ""

def test_facebook_navigation_and_readiness():
    account_id = "test_account_01"
    log_info(f"--- TESTING FACEBOOK NAVIGATION & UI READINESS [ACCOUNT: {account_id}] ---", tag="NAV_TEST")

    bm = BrowserManager(
        account_id=account_id,
        debug_mode=True,
        headless=False,
        window_width=500,
        window_height=600,
        slow_mo=300
    )

    try:
        page = bm.launch()
        log_info("[BROWSER] Navigation started", tag="NAV_TEST")
        bm.navigate("https://www.facebook.com/")

        # Execute state-based Facebook UI readiness check
        is_ready = bm.wait_for_facebook_ready(timeout_seconds=30)

        if not is_ready:
            log_error("[BROWSER ERROR] Facebook UI did not become ready", tag="NAV_TEST")
            log_error(f"[NAV_TEST] Final URL: {page.url}", tag="NAV_TEST")
            try:
                log_error(f"[NAV_TEST] Final Title: {page.title()}", tag="NAV_TEST")
            except Exception:
                pass
            print("\n" + "="*60)
            print("[NAV_TEST] Facebook UI readiness test FAILED.")
            print("[NAV_TEST] Browser kept open for manual observation.")
            safe_input("[NAV_TEST] Press ENTER to close browser... ")
            print("="*60 + "\n")
            bm.close()
            return False

        # Print URL and Title
        current_url = page.url
        try:
            current_title = page.title()
        except Exception:
            current_title = "Facebook"

        log_info(f"[NAV_TEST] Facebook URL: {current_url}", tag="NAV_TEST")
        log_info(f"[NAV_TEST] Facebook Title: {current_title}", tag="NAV_TEST")

        # Session Verification ONLY after UI readiness
        log_info("[NAV_TEST] Inspecting session status after UI readiness...", tag="NAV_TEST")
        sm = SessionManager(bm)
        session_status = sm.check_session(page)
        log_info(f"[NAV_TEST] Session Status: {session_status.value}", tag="NAV_TEST")

        print("\n" + "="*60)
        print("[NAV_TEST] Facebook UI Readiness Test PASSED!")
        print(f"[NAV_TEST] Current URL: {current_url}")
        print(f"[NAV_TEST] Current Title: {current_title}")
        print(f"[NAV_TEST] Session Status: {session_status.value}")
        print("[NAV_TEST] Browser will remain open for manual observation.")
        safe_input("[NAV_TEST] Press ENTER in this terminal when ready to close browser... ")
        print("="*60 + "\n")

        bm.close()
        log_info("[NAV_TEST] Browser closed cleanly.", tag="NAV_TEST")
        return True

    except Exception as e:
        log_error(f"[NAV_TEST ERROR] Exception during navigation test: {str(e)}", tag="NAV_TEST")
        log_error(f"Traceback:\n{traceback.format_exc()}", tag="NAV_TEST")
        if bm:
            bm.close()
        return False

if __name__ == "__main__":
    success = test_facebook_navigation_and_readiness()
    sys.exit(0 if success else 1)
