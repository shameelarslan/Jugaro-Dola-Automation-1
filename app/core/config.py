"""
App Configuration & Setting Defaults for Dola Bulk Video Automation Software.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field

from app.core.version import get_base_dir, get_data_dir

BASE_DIR = get_base_dir()
DATA_DIR = get_data_dir()
DB_PATH = DATA_DIR / "dola_automation.db"
DEFAULT_DOWNLOAD_DIR = str(Path.home() / "Downloads" / "Dola_Videos")
DEFAULT_EXTENSION_PATH = ""

@dataclass
class AppConfig:
    # Storage & Compatibility
    extension_path: str = ""
    default_download_dir: str = DEFAULT_DOWNLOAD_DIR
    separate_batch_folders: bool = True
    
    # Automation Defaults (Generate Videos Workflow)
    default_model: str = "Seedance 2.5"
    default_ratio: str = "9:16"
    total_sessions_to_run: int = 10         # Range: 1 - 100
    videos_per_session: int = 15            # Range: 1 - 15
    sessions_at_a_time: int = 3             # Range: 1 - 50
    concurrency_limit: int = 3              # Backward-compatible alias for sessions_at_a_time
    tab_launch_delay_sec: float = 5.0       # 5-second delay before creating next tab
    
    # Watermark Remover Settings (Built-in Blur Method)
    enable_watermark_remover: bool = True
    blur_x: int = 540
    blur_y: int = 1220
    blur_w: int = 170
    blur_h: int = 50

    # Dola Confirmation & Response Settings
    confirmation_response_text: str = "start generation."
    
    # Timeouts & Intervals
    generation_timeout_sec: int = 480       # 8 minutes for video generation
    download_button_timeout_sec: int = 600   # 10 minutes total wait
    polling_interval_sec: float = 2.0        # Check DOM every 2 seconds
    download_verification_timeout_sec: int = 60 # 60 sec file write stability check
    
    # Queue & Assignment Settings
    assignment_mode: str = "rolling_pool"   # "rolling_pool" or "one_to_one"
    auto_reassign_failed_session: bool = False
    
    # Retry Policy
    max_retries: int = 3
    retry_delay_sec: int = 5
    
    # Browser Settings
    headless_mode: bool = False             # Extensions require headed window context
    browser_executable_path: str = ""       # Blank uses Playwright bundled Chromium
    
    # Onboarding Tutorial
    tutorial_completed: bool = False        # Tracks whether user has seen or skipped the first-time tour

    def to_dict(self) -> dict:
        return {
            "extension_path": getattr(self, "extension_path", ""),
            "default_download_dir": self.default_download_dir,
            "separate_batch_folders": self.separate_batch_folders,
            "default_model": self.default_model,
            "default_ratio": self.default_ratio,
            "total_sessions_to_run": self.total_sessions_to_run,
            "videos_per_session": self.videos_per_session,
            "sessions_at_a_time": self.sessions_at_a_time,
            "concurrency_limit": self.sessions_at_a_time,
            "tab_launch_delay_sec": self.tab_launch_delay_sec,
            "confirmation_response_text": self.confirmation_response_text,
            "generation_timeout_sec": self.generation_timeout_sec,
            "download_button_timeout_sec": self.download_button_timeout_sec,
            "polling_interval_sec": self.polling_interval_sec,
            "download_verification_timeout_sec": self.download_verification_timeout_sec,
            "enable_watermark_remover": self.enable_watermark_remover,
            "blur_x": self.blur_x,
            "blur_y": self.blur_y,
            "blur_w": self.blur_w,
            "blur_h": self.blur_h,
            "assignment_mode": self.assignment_mode,
            "auto_reassign_failed_session": self.auto_reassign_failed_session,
            "max_retries": self.max_retries,
            "retry_delay_sec": self.retry_delay_sec,
            "headless_mode": self.headless_mode,
            "browser_executable_path": self.browser_executable_path,
            "tutorial_completed": getattr(self, "tutorial_completed", False)
        }
