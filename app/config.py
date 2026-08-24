"""
Backward compatibility configuration shim.
Re-exports core config items and legacy path constants.
"""

from app.core.config import *

LOGS_DIR = DATA_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

ACCOUNTS_DIR = DATA_DIR / "accounts"
ACCOUNTS_DIR.mkdir(parents=True, exist_ok=True)

INPUT_DIR = DATA_DIR / "input"
INPUT_DIR.mkdir(parents=True, exist_ok=True)

ARCHIVE_DIR = DATA_DIR / "archive"
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

SCREENSHOTS_DIR = DATA_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

FB_DESKTOP_URL = "https://www.facebook.com"
DEFAULT_DEBUG_MODE = False
DEFAULT_HEADLESS = False
DEFAULT_SLOW_MO = 50
DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 800
DEFAULT_DESKTOP_VIEWPORT = {"width": 1280, "height": 800}
DEFAULT_DESKTOP_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
