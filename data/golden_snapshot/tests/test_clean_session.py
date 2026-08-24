import sys
import time
import traceback
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.browser.browser_manager import BrowserManager
from app.browser.session_manager import SessionManager, SessionStatus

def run_clean_session_test(timeout_seconds=600):
    account_id = "test_account_01"

    print("--- STARTING CLEAN SESSION TEST ---")
    print(f"[SESSION TEST] Using primary test account: {account_id}")

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
        print("[SESSION TEST] Browser visible")

        sm = SessionManager(bm)
        bm.navigate("https://www.facebook.com/")
        print("[SESSION TEST] Facebook opened")

        initial_status, _, _ = sm.inspect_single_snapshot(page)

        if initial_status != SessionStatus.LOGGED_IN:
            print("[SESSION TEST] LOGIN REQUIRED")
            print("[SESSION TEST] Please login manually in the visible browser (including any 2FA / approval steps).")
            print("[SESSION TEST] Waiting for manual login...")

            login_success = sm.wait_for_manual_login(page, timeout_seconds=timeout_seconds)

            if not login_success:
                print("[SESSION TEST] Manual login timed out or failed.")
                bm.close()
                return False

        status, signals = sm.verify_stable_authenticated_state(page, required_checks=3, check_interval=1.0)
        current_url = page.url

        if status == SessionStatus.LOGGED_IN:
            print("\n" + "="*60)
            print("[SESSION TEST] STATUS: LIVE")
            print(f"[SESSION TEST] Strong authenticated signals: {signals}")
            print(f"[SESSION TEST] URL: {current_url}")
            print("[SESSION TEST] Verification stable: YES")
            print("="*60 + "\n")
        else:
            print(f"[SESSION TEST] Verification failed stability check. Status: {status.value}")
            bm.close()
            return False

        print("[SESSION TEST] The browser will REMAIN VISIBLE on your desktop.")
        print("[SESSION TEST] Please visually inspect your Facebook page.")
        try:
            input("[SESSION TEST] Press ENTER in this terminal when ready to close browser... ")
        except (EOFError, KeyboardInterrupt):
            pass
        print("="*60 + "\n")

        bm.close()
        print("[SESSION TEST] Browser closed cleanly.")
        return True

    except Exception as e:
        print(f"[SESSION ERROR] Observation test failed: {str(e)}")
        print(traceback.format_exc())
        if bm:
            bm.close()
        return False

if __name__ == "__main__":
    success = run_clean_session_test()
    sys.exit(0 if success else 1)
