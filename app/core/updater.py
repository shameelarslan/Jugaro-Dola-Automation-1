"""
Cloud Auto-Updater Engine for Waqas Automation Pro.
Checks Supabase Cloud for new application releases, downloads hotfix patches / updates,
and installs them seamlessly via Detached Native Updater & Disk Runtime Hooks.
"""

import os
import sys
import json
import shutil
import zipfile
import tempfile
import subprocess
import urllib.request
from packaging import version
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from app.core.logger import logger
from app.core.cloud_manager import cloud_manager

CURRENT_VERSION = "2.1.2"
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
VERSION_FILE = DATA_DIR / "app_version.txt"

def _is_newer_semver(latest: str, current: str) -> bool:
    try:
        return version.parse(latest) > version.parse(current)
    except Exception:
        try:
            l_parts = [int(p) for p in latest.replace("v", "").split(".")]
            c_parts = [int(p) for p in current.replace("v", "").split(".")]
            return l_parts > c_parts
        except Exception:
            return False

def get_installed_version() -> str:
    """Reads installed version from data/app_version.txt or falls back to CURRENT_VERSION."""
    if VERSION_FILE.exists():
        try:
            v = VERSION_FILE.read_text(encoding="utf-8").strip()
            if v:
                # If code version is newer than stored version, auto-sync
                if _is_newer_semver(CURRENT_VERSION, v):
                    set_installed_version(CURRENT_VERSION)
                    return CURRENT_VERSION
                return v
        except Exception:
            pass
    set_installed_version(CURRENT_VERSION)
    return CURRENT_VERSION

def set_installed_version(ver: str):
    """Persists updated version string to disk."""
    try:
        VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        VERSION_FILE.write_text(ver.strip(), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Could not save version file: {e}", category="UPDATER")

class AutoUpdater:
    """Singleton Cloud Update Engine."""
    _instance: Optional["AutoUpdater"] = None

    def __init__(self):
        self.current_version = get_installed_version()
        self.latest_release: Optional[Dict[str, Any]] = None
        self.is_detached_updater_active: bool = False

    @classmethod
    def get_instance(cls) -> "AutoUpdater":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def check_for_updates(self, user_email: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Synchronously queries Supabase for the latest active release.
        Returns (is_update_available, release_dict).
        """
        self.current_version = get_installed_version()

        try:
            client = cloud_manager.client
            if not client:
                return False, None

            curr_email = ""
            if user_email:
                curr_email = str(user_email).strip().lower()
            elif cloud_manager.current_user:
                curr_email = str(cloud_manager.current_user.get("email") or "").strip().lower()

            res = client.table("app_releases") \
                .select("*") \
                .eq("is_active", True) \
                .order("id", desc=True) \
                .execute()

            if not res.data or len(res.data) == 0:
                return False, None

            applicable_release = None
            for rel in res.data:
                target = (rel.get("target_email") or "*").strip().lower()
                if target and target != "*":
                    allowed_targets = [e.strip().lower() for e in target.replace(";", ",").split(",") if e.strip()]
                    if "admin" in allowed_targets:
                        from app.core.cloud_manager import ADMIN_EMAILS
                        user_role = cloud_manager.current_user.get("role", "") if cloud_manager.current_user else ""
                        is_user_admin = (curr_email in [e.lower() for e in ADMIN_EMAILS]) or (user_role.lower() == "admin")
                        if not is_user_admin:
                            continue
                    elif curr_email not in allowed_targets and curr_email != target:
                        continue
                applicable_release = rel
                break

            if not applicable_release:
                return False, None

            latest_ver_str = applicable_release.get("version", "").strip()

            if self._is_newer_version(latest_ver_str, self.current_version):
                self.latest_release = applicable_release
                logger.info(f"🚀 Cloud Auto-Updater: New version v{latest_ver_str} found for admin {curr_email} (Current: v{self.current_version})", category="UPDATER")
                return True, applicable_release

            return False, None
        except Exception as e:
            logger.warning(f"Auto-update check failed (non-critical): {e}", category="UPDATER")
            return False, None

    def _is_newer_version(self, latest: str, current: str) -> bool:
        """Compares two semver version strings safely."""
        try:
            return version.parse(latest) > version.parse(current)
        except Exception:
            try:
                l_parts = [int(p) for p in latest.replace("v", "").split(".")]
                c_parts = [int(p) for p in current.replace("v", "").split(".")]
                return l_parts > c_parts
            except Exception:
                return False

    def download_and_install_update(self, download_url: str, version_str: str = "", progress_callback=None) -> bool:
        """
        Downloads update package, extracts files, and prepares detached runner for clean restart.
        """
        if not download_url:
            logger.error("Download URL is empty for update", category="UPDATER")
            return False

        new_ver = version_str.strip() or (self.latest_release.get("version", "") if self.latest_release else "2.0.7")

        try:
            temp_dir = tempfile.mkdtemp(prefix="waqas_update_")
            is_installer_exe = download_url.lower().split("?")[0].endswith(".exe")

            logger.info(f"Downloading update from {download_url}...", category="UPDATER")

            # Progress hook
            def _report_progress(count, block_size, total_size):
                if progress_callback and total_size > 0:
                    percent = int((count * block_size * 100) / total_size)
                    progress_callback(min(100, percent))

            req = urllib.request.Request(
                download_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) WaqasAutomationPro/2.0.5"}
            )

            if is_installer_exe:
                # Direct Setup Installer Download
                setup_file = os.path.join(temp_dir, "WaqasAutomationPro_Setup.exe")
                with urllib.request.urlopen(req) as response, open(setup_file, "wb") as out_file:
                    total_size = int(response.headers.get("Content-Length", 0))
                    bytes_dl = 0
                    chunk_size = 64 * 1024
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        out_file.write(chunk)
                        bytes_dl += len(chunk)
                        if progress_callback and total_size > 0:
                            progress_callback(min(100, int((bytes_dl * 100) / total_size)))

                logger.info("Executing standalone installer in background...", category="UPDATER")
                subprocess.Popen([setup_file], close_fds=True)
                self.is_detached_updater_active = True
                set_installed_version(new_ver)
                return True

            # Standard Zip Patch Download
            zip_path = os.path.join(temp_dir, "update.zip")
            with urllib.request.urlopen(req) as response, open(zip_path, "wb") as out_file:
                total_size = int(response.headers.get("Content-Length", 0))
                bytes_dl = 0
                chunk_size = 64 * 1024
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    bytes_dl += len(chunk)
                    if progress_callback and total_size > 0:
                        progress_callback(min(100, int((bytes_dl * 100) / total_size)))

            # Extract zip
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)

            # Determine true content root inside extracted zip
            source_content_dir = extract_dir
            subfolders = [os.path.join(extract_dir, d) for d in os.listdir(extract_dir) if os.path.isdir(os.path.join(extract_dir, d))]
            if len(subfolders) == 1 and not any(os.path.isfile(os.path.join(extract_dir, f)) for f in os.listdir(extract_dir)):
                source_content_dir = subfolders[0]

            is_frozen = getattr(sys, 'frozen', False)

            if is_frozen:
                # Target app installation directory
                app_exe = sys.executable
                install_dir = os.path.abspath(os.path.dirname(app_exe))
                helper_exe = os.path.join(source_content_dir, "UpdateHelper.exe")
                curr_pid = os.getpid()

                DETACHED_FLAGS = 0x00000008 | 0x00000200 if os.name == 'nt' else 0

                if os.path.exists(helper_exe):
                    logger.info(f"Triggering high-reliability UpdateHelper: {helper_exe}", category="UPDATER")
                    subprocess.Popen(
                        [helper_exe, "--source", source_content_dir, "--target", install_dir, "--exe", "WaqasAutomationPro.exe", "--pid", str(curr_pid)],
                        creationflags=DETACHED_FLAGS,
                        close_fds=True
                    )
                else:
                    # Create standalone Detached Batch Updater Script as fallback
                    bat_path = os.path.join(temp_dir, "apply_update.bat")
                    bat_script_content = f"""@echo off
setlocal enabledelayedexpansion
title Waqas Automation Pro Auto-Updater
echo ======================================================
echo  Applying Waqas Automation Pro Update v{new_ver}...
echo  Please wait a moment while files are being updated.
echo ======================================================

:: Force close any remaining application instances to release file locks
taskkill /F /IM WaqasAutomationPro.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: Sync root files and binaries (overwrites WaqasAutomationPro.exe while preserving user databases and sessions)
robocopy "{source_content_dir}" "{install_dir}" /E /R:10 /W:1 /XD "data" "logs" /XF "*.db" "*.db-wal" "*.db-shm" "user_session.json" /NJH /NJS /NDL /NC /NS

:: Ensure version text is updated
if not exist "{install_dir}\\data" mkdir "{install_dir}\\data"
echo {new_ver}> "{install_dir}\\data\\app_version.txt"

:: Also update sitecustomize, app, and ui inside _internal if present
if exist "{install_dir}\\_internal" (
    if exist "{source_content_dir}\\sitecustomize.py" copy /Y "{source_content_dir}\\sitecustomize.py" "{install_dir}\\_internal\\sitecustomize.py" >nul
    if exist "{source_content_dir}\\app" robocopy "{source_content_dir}\\app" "{install_dir}\\_internal\\app" /E /R:5 /W:1 /NJH /NJS /NDL /NC /NS
    if exist "{source_content_dir}\\ui" robocopy "{source_content_dir}\\ui" "{install_dir}\\_internal\\ui" /E /R:5 /W:1 /NJH /NJS /NDL /NC /NS
    if exist "{source_content_dir}\\data\\viral_prompts" robocopy "{source_content_dir}\\data\\viral_prompts" "{install_dir}\\_internal\\data\\viral_prompts" /E /R:5 /W:1 /NJH /NJS /NDL /NC /NS
    if exist "{source_content_dir}\\_internal" robocopy "{source_content_dir}\\_internal" "{install_dir}\\_internal" /E /R:5 /W:1 /NJH /NJS /NDL /NC /NS
)

:: Launch the updated application
echo Starting updated Waqas Automation Pro v{new_ver}...
start "" "{app_exe}"

:: Cleanup temporary update files
ping 127.0.0.1 -n 3 >nul
rd /s /q "{temp_dir}" 2>nul
exit
"""
                    with open(bat_path, "w", encoding="utf-8") as bf:
                        bf.write(bat_script_content)

                    logger.info(f"Triggering fallback detached updater script: {bat_path}", category="UPDATER")
                    subprocess.Popen(
                        ["cmd.exe", "/c", bat_path],
                        creationflags=DETACHED_FLAGS,
                        close_fds=True
                    )

                self.is_detached_updater_active = True
                set_installed_version(new_ver)
                self.current_version = new_ver
                logger.info(f"✅ Detached updater initiated for v{new_ver}", category="UPDATER")
                return True

            else:
                # Non-frozen development environment
                app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

                for root, dirs, files in os.walk(source_content_dir):
                    rel_path = os.path.relpath(root, source_content_dir)
                    target_folder = os.path.join(app_root, rel_path) if rel_path != "." else app_root
                    os.makedirs(target_folder, exist_ok=True)

                    for f in files:
                        if f.endswith((".db", ".db-wal", ".db-shm")) or f == "user_session.json":
                            continue
                        src_f = os.path.join(root, f)
                        dest_f = os.path.join(target_folder, f)
                        try:
                            shutil.copy2(src_f, dest_f)
                        except Exception as e:
                            logger.warning(f"Could not overwrite {dest_f}: {e}", category="UPDATER")

                set_installed_version(new_ver)
                self.current_version = new_ver
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info(f"✅ Dev Update to v{new_ver} applied cleanly!", category="UPDATER")
                return True

        except Exception as e:
            logger.error(f"Failed to download and install update: {e}", category="UPDATER")
            return False

updater = AutoUpdater.get_instance()
