import os
from datetime import datetime
from pathlib import Path
from config import SCREENSHOTS_DIR
from app.utils.logger import log_info, log_error

def capture_screenshot(page_or_context, name_prefix="error"):
    """
    Captures a screenshot with a strict 5-second bounded timeout.
    Prevents screenshot capture from causing secondary 30-second timeouts.
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name_prefix}_{timestamp}.png"
        filepath = SCREENSHOTS_DIR / filename

        target_page = None
        if hasattr(page_or_context, "screenshot"):
            target_page = page_or_context
        elif hasattr(page_or_context, "pages") and page_or_context.pages:
            target_page = page_or_context.pages[0]

        if target_page:
            try:
                target_page.screenshot(path=str(filepath), full_page=False, timeout=5000)
                log_info(f"Screenshot saved: {filepath}", tag="SCREENSHOT")
                return str(filepath)
            except Exception as ss_err:
                log_error(f"Bounded screenshot capture timed out/failed: {str(ss_err)}", tag="SCREENSHOT")
                return None
        else:
            log_error("Failed to capture screenshot: Invalid Playwright object", tag="SCREENSHOT")
            return None
    except Exception as e:
        log_error(f"Failed to capture screenshot: {str(e)}", tag="SCREENSHOT")
        return None
