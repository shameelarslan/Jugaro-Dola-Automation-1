import sys
import time
import traceback
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.browser.browser_manager import BrowserManager

def run_browser_manager_visible_test():
    print("[BROWSER MANAGER TEST] Starting")
    
    try:
        bm = BrowserManager(
            account_id="test_account_01",
            debug_mode=True,
            headless=False,
            window_width=500,
            window_height=600,
            slow_mo=300
        )
        print("[BROWSER MANAGER TEST] BrowserManager initialized")
        print(f"[BROWSER MANAGER TEST] Debug={bm.debug_mode}")
        print(f"[BROWSER MANAGER TEST] Headless={bm.headless}")
        
        print("[BROWSER MANAGER TEST] Launching browser...")
        page = bm.launch()
        
        is_connected = bm.context is not None and (
            bm.context.browser.is_connected() if bm.context.browser else True
        )
        print(f"[BROWSER MANAGER TEST] Browser connected={is_connected}")
        print(f"[BROWSER MANAGER TEST] Page created={page is not None}")
        
        bm.navigate("https://www.facebook.com/")
        print(f"[BROWSER MANAGER TEST] URL={page.url}")
        print("[BROWSER MANAGER TEST] Browser should be physically visible")
        print("[BROWSER MANAGER TEST] Waiting for manual close")

        # Keep browser open indefinitely until user manually closes Chromium window
        try:
            while bm.context and bm.context.pages:
                page.wait_for_timeout(1000)
        except Exception:
            pass

        bm.close()
        print("[BROWSER MANAGER TEST] Browser window closed cleanly.")

    except Exception as e:
        print(f"[BROWSER MANAGER TEST] Exception occurred during launch: {str(e)}")
        print(traceback.format_exc())

if __name__ == "__main__":
    run_browser_manager_visible_test()
