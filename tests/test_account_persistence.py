import sys
import time
import traceback
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.browser.browser_manager import BrowserManager
from app.browser.session_manager import SessionManager, SessionStatus
from app.utils.logger import log_info, log_error, log_warning

def safe_input(prompt_msg):
    try:
        return input(prompt_msg)
    except (EOFError, KeyboardInterrupt):
        print("\n[ACCOUNT TEST] Terminal input finished.")
        return ""

def run_account_persistence_test(timeout_seconds=600):
    account_id = "test_account_01"
    expected_profile_rel = f"data/accounts/{account_id}/user_data/"

    print("\n" + "="*60)
    print("--- STARTING PERMANENT ACCOUNT SESSION PERSISTENCE TEST ---")
    print(f"[ACCOUNT TEST] Primary Account ID: {account_id}")
    print(f"[ACCOUNT TEST] Expected Persistent Profile Path: {expected_profile_rel}")
    print("="*60 + "\n")

    # =========================================================================
    # RUN 1: Initial Launch, Manual Login (if required), and Verification
    # =========================================================================
    print("=== RUN 1: Launching Primary Test Account Profile ===")
    bm1 = BrowserManager(
        account_id=account_id,
        debug_mode=True,
        headless=False,
        window_width=500,
        window_height=600,
        slow_mo=300
    )

    try:
        page1 = bm1.launch()
        sm1 = SessionManager(bm1)

        bm1.navigate("https://www.facebook.com/")
        if not bm1.wait_for_facebook_ready(timeout_seconds=30):
            print("[ACCOUNT TEST ERROR] Facebook UI did not become ready during Run 1.")
            bm1.close()
            return False

        status1, _, _ = sm1.inspect_single_snapshot(page1)

        if status1 != SessionStatus.LOGGED_IN:
            print("[ACCOUNT TEST] LOGIN REQUIRED")
            print("[ACCOUNT TEST] Please manually login in the visible browser.")
            print("[ACCOUNT TEST] Complete any 2FA/security approval.")
            print("[ACCOUNT TEST] Waiting for LIVE...")

            login_success = sm1.wait_for_manual_login(page1, timeout_seconds=timeout_seconds)
            if not login_success:
                print("[ACCOUNT TEST ERROR] Manual login was not completed within timeout.")
                bm1.close()
                return False

        # Final stability check for Run 1
        live_status1, signals1 = sm1.verify_stable_authenticated_state(page1, required_checks=3, check_interval=1.0)
        if live_status1 != SessionStatus.LOGGED_IN:
            print(f"[ACCOUNT TEST ERROR] Run 1 failed stability verification ({live_status1.value}).")
            bm1.close()
            return False

        print("\n" + "="*60)
        print("[ACCOUNT TEST] LIVE CONFIRMED")
        print(f"[ACCOUNT TEST] Persistent profile: {expected_profile_rel}")
        print(f"[ACCOUNT TEST] Signals: {signals1}")
        print("="*60 + "\n")

        print("[ACCOUNT TEST] Browser remains visible on your screen.")
        safe_input("[ACCOUNT TEST] Press ENTER in this terminal when ready to close browser for RUN 1... ")
        bm1.close()
        print("=== RUN 1 Completed & Browser Closed Cleanly. ===\n")

    except Exception as e:
        print(f"[ACCOUNT TEST ERROR] Exception during Run 1: {str(e)}")
        print(traceback.format_exc())
        if bm1:
            bm1.close()
        return False

    time.sleep(3)

    # =========================================================================
    # RUN 2: Reopen EXACT SAME Profile & Verify Persistence Without Login Prompt
    # =========================================================================
    print("=== RUN 2: Reopening EXACT SAME Profile Directory ===")
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

        bm2.navigate("https://www.facebook.com/")
        if not bm2.wait_for_facebook_ready(timeout_seconds=30):
            print("[ACCOUNT TEST ERROR] Facebook UI did not become ready during Run 2.")
            bm2.close()
            return False

        status2, signals2 = sm2.verify_stable_authenticated_state(page2, required_checks=3, check_interval=1.0)

        if status2 == SessionStatus.LOGGED_IN:
            print("\n" + "="*60)
            print("[ACCOUNT TEST] Existing session detected")
            print("[ACCOUNT TEST] Status: LIVE")
            print("[ACCOUNT TEST] PERSISTENT LOGIN VERIFIED")
            print(f"[ACCOUNT TEST] Account ID: {account_id}")
            print(f"[ACCOUNT TEST] Profile Path: {expected_profile_rel}")
            print(f"[ACCOUNT TEST] Signals: {signals2}")
            print("="*60 + "\n")

            print("[ACCOUNT TEST] Browser remains visible for manual confirmation.")
            safe_input("[ACCOUNT TEST] Press ENTER in this terminal to close browser and complete test... ")
            bm2.close()
            print("\n--- ACCOUNT PERSISTENCE TEST COMPLETED SUCCESSFULLY ---")
            return True
        else:
            print("\n" + "="*60)
            print(f"[ACCOUNT TEST ERROR] Persistent login FAILED. Status on restart: {status2.value}")
            print("="*60 + "\n")
            bm2.close()
            return False

    except Exception as e:
        print(f"[ACCOUNT TEST ERROR] Exception during Run 2: {str(e)}")
        print(traceback.format_exc())
        if bm2:
            bm2.close()
        return False

if __name__ == "__main__":
    success = run_account_persistence_test()
    sys.exit(0 if success else 1)
