import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.browser.browser_manager import BrowserManager
from app.browser.session_manager import SessionManager
from app.utils.logger import log_info, log_error

def test_independent_browser_launch():
    """
    Independent Browser Launch Verification Script.
    Launches Chromium desktop browser in Debug Mode (window visible, 400x400),
    navigates to Facebook desktop URL, checks session, captures screenshot, and closes cleanly.
    """
    log_info("--- STARTING INDEPENDENT BROWSER LAUNCH TEST ---", tag="TEST")

    bm = BrowserManager(
        account_id="test_account_01",
        debug_mode=True,
        window_width=400,
        window_height=400,
        slow_mo=300,
    )

    try:
        page = bm.launch()
        log_info("Browser launched. Navigating to Facebook Desktop...", tag="TEST")
        bm.navigate("https://www.facebook.com")

        log_info("Checking Facebook session state...", tag="TEST")
        session_mgr = SessionManager(bm)
        is_logged_in = session_mgr.check_session(page)
        log_info(f"Session Status: {'LOGGED IN' if is_logged_in else 'LOGIN REQUIRED'}", tag="TEST")

        # Capture a verification screenshot
        screenshot_path = bm.capture_error("browser_launch_test")
        log_info(f"Verification screenshot captured: {screenshot_path}", tag="TEST")

        time.sleep(2)  # Keep window open briefly for human observation
        bm.close()
        log_info("--- INDEPENDENT BROWSER LAUNCH TEST COMPLETED SUCCESSFULLY ---", tag="TEST")
        return True
    except Exception as e:
        log_error(f"--- INDEPENDENT BROWSER LAUNCH TEST FAILED: {str(e)} ---", tag="TEST")
        if bm:
            bm.close()
        return False

if __name__ == "__main__":
    success = test_independent_browser_launch()
    sys.exit(0 if success else 1)
