import sys
import time
import traceback
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.automation.state_machine import StateMachine
from app.utils.logger import log_info, log_error

def safe_input(prompt_msg):
    try:
        return input(prompt_msg)
    except (EOFError, KeyboardInterrupt):
        print("\n[PAGE TEST] Non-interactive input detected.")
        return ""

def run_page_switch_standalone_test(target_page_name="Huang"):
    account_id = "test_account_01"

    print("\n" + "="*60)
    print("--- STARTING MILESTONE 3: REAL PAGE SWITCHING TEST ---")
    print(f"[ACCOUNT] {account_id}")
    print(f"[TARGET PAGE] {target_page_name}")
    print("="*60 + "\n")

    sm_engine = StateMachine(account_id=account_id, target_page=target_page_name)

    try:
        success = sm_engine.run_page_switch_workflow()

        if success:
            print("\n" + "="*60)
            print(f"[PAGE TEST] Target Page '{target_page_name}' is VERIFIED ACTIVE.")
            print("[PAGE TEST] Browser remains open for visual inspection.")
            safe_input("[PAGE TEST] Press ENTER in this terminal when ready to close browser... ")
            print("="*60 + "\n")
            if sm_engine.bm:
                sm_engine.bm.close()
            return True
        else:
            print("\n" + "="*60)
            print("[PAGE TEST] Page switching verification FAILED / SAFE STOP triggered.")
            print("[PAGE TEST] Browser kept open for inspection.")
            safe_input("[PAGE TEST] Press ENTER in this terminal when ready to close browser... ")
            print("="*60 + "\n")
            if sm_engine.bm:
                sm_engine.bm.close()
            return False

    except Exception as e:
        print(f"[PAGE ERROR] Test execution error: {str(e)}")
        print(traceback.format_exc())
        if sm_engine.bm:
            sm_engine.bm.close()
        return False

if __name__ == "__main__":
    target_name = sys.argv[1] if len(sys.argv) > 1 else "Huang"
    success = run_page_switch_standalone_test(target_name)
    sys.exit(0 if success else 1)
