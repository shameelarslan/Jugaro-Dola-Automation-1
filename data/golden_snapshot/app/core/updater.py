"""
Cloud Auto-Updater Engine for Waqas Automation Pro.
Checks Supabase Cloud for new application releases, downloads hotfix patches / updates,
and installs them seamlessly.
"""

import os
import sys
import json
import shutil
import zipfile
import tempfile
import urllib.request
from packaging import version
from typing import Optional, Dict, Any, Tuple
from app.core.logger import logger
from app.core.cloud_manager import cloud_manager

CURRENT_VERSION = "2.0.0"

class AutoUpdater:
    """Singleton Cloud Update Engine."""
    _instance: Optional["AutoUpdater"] = None

    def __init__(self):
        self.current_version = CURRENT_VERSION
        self.latest_release: Optional[Dict[str, Any]] = None

    @classmethod
    def get_instance(cls) -> "AutoUpdater":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def check_for_updates(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Synchronously queries Supabase for the latest active release.
        Returns (is_update_available, release_dict).
        """
        try:
            client = cloud_manager.client
            if not client:
                return False, None

            res = client.table("app_releases") \
                .select("*") \
                .eq("is_active", True) \
                .order("id", desc=True) \
                .limit(1) \
                .execute()

            if not res.data or len(res.data) == 0:
                return False, None

            latest = res.data[0]
            latest_ver_str = latest.get("version", "").strip()

            if self._is_newer_version(latest_ver_str, self.current_version):
                self.latest_release = latest
                logger.info(f"🚀 Cloud Auto-Updater: New version v{latest_ver_str} found (Current: v{self.current_version})", category="UPDATER")
                return True, latest

            return False, None
        except Exception as e:
            logger.warning(f"Auto-update check failed (non-critical): {e}", category="UPDATER")
            return False, None

    def _is_newer_version(self, latest: str, current: str) -> bool:
        """Compares two semver version strings safely."""
        try:
            return version.parse(latest) > version.parse(current)
        except Exception:
            # Fallback simple tuple split
            try:
                l_parts = [int(p) for p in latest.replace("v", "").split(".")]
                c_parts = [int(p) for p in current.replace("v", "").split(".")]
                return l_parts > c_parts
            except Exception:
                return False

    def download_and_install_update(self, download_url: str, progress_callback=None) -> bool:
        """
        Downloads the update zip, extracts files over current installation, and prepares restart.
        """
        if not download_url:
            logger.error("Download URL is empty for update", category="UPDATER")
            return False

        try:
            temp_dir = tempfile.mkdtemp(prefix="waqas_update_")
            zip_path = os.path.join(temp_dir, "update.zip")

            logger.info(f"Downloading update from {download_url}...", category="UPDATER")
            
            # Download with progress report
            def _report_progress(count, block_size, total_size):
                if progress_callback and total_size > 0:
                    percent = int((count * block_size * 100) / total_size)
                    progress_callback(min(100, percent))

            urllib.request.urlretrieve(download_url, zip_path, reporthook=_report_progress)

            # Extract zip
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)

            # Target app root
            app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

            # Overwrite files cleanly
            for root, dirs, files in os.walk(extract_dir):
                rel_path = os.path.relpath(root, extract_dir)
                target_folder = os.path.join(app_root, rel_path) if rel_path != "." else app_root
                os.makedirs(target_folder, exist_ok=True)

                for f in files:
                    src_f = os.path.join(root, f)
                    dest_f = os.path.join(target_folder, f)
                    try:
                        shutil.copy2(src_f, dest_f)
                    except Exception as e:
                        logger.warning(f"Could not overwrite {dest_f}: {e}", category="UPDATER")

            # Clean temp
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.info("✅ Update successfully downloaded and extracted!", category="UPDATER")
            return True

        except Exception as e:
            logger.error(f"Failed to download and install update: {e}", category="UPDATER")
            return False

updater = AutoUpdater.get_instance()
