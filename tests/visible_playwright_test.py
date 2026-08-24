import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import DEFAULT_DESKTOP_VIEWPORT, DEFAULT_DESKTOP_USER_AGENT

def run_visible_playwright_test():
    print("[PLAYWRIGHT TEST] Starting")
    print("[PLAYWRIGHT TEST] headless=False")
    print("[PLAYWRIGHT TEST] Launching Chromium...")

    profile_dir = BASE_DIR / "data" / "test_playwright_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        args = [
            "--window-size=500,600",
            "--window-position=100,100",
            "--disable-notifications",
            "--no-sandbox",
        ]

        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            args=args,
            viewport=DEFAULT_DESKTOP_VIEWPORT,
            is_mobile=False,
            has_touch=False,
            user_agent=DEFAULT_DESKTOP_USER_AGENT,
        )
        print("[PLAYWRIGHT TEST] Browser launched")
        print("[PLAYWRIGHT TEST] Context created")

        page = context.pages[0] if context.pages else context.new_page()
        print("[PLAYWRIGHT TEST] Page created")

        page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
        print(f"[PLAYWRIGHT TEST] URL: {page.url}")
        print("[PLAYWRIGHT TEST] Browser should now be visible")
        print("[PLAYWRIGHT TEST] Waiting for manual browser close")

        # Keep browser open until user manually closes the Chromium window
        try:
            while context.pages:
                page.wait_for_timeout(1000)
        except Exception:
            pass

        print("[PLAYWRIGHT TEST] Browser window closed cleanly.")

if __name__ == "__main__":
    run_visible_playwright_test()
