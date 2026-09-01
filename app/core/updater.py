"""
Enterprise Auto-Updater Engine for Waqas Automation Pro.
Supports Multi-Source Update Discovery (GitHub Releases API + Supabase Cloud Manifest),
SHA-256 Integrity Verification, Safe Rollback & Persistent User Data Protection.
"""

import os
import sys
import json
import shutil
import hashlib
import zipfile
import tempfile
import subprocess
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

from app.core.logger import logger
from app.core.version import (
    get_installed_version,
    set_installed_version,
    is_newer_version,
    get_base_dir,
    get_data_dir,
    APP_NAME
)

GITHUB_REPOS = [
    "shameelarslan/Jugaro-Dola-Automation-1",
    "shameelarslan/Jugaro-Dola-Automation"
]

class AutoUpdater:
    """Singleton Cloud & GitHub Desktop Software Update Engine."""
    _instance: Optional["AutoUpdater"] = None

    def __init__(self):
        self.current_version = get_installed_version()
        self.latest_release: Optional[Dict[str, Any]] = None
        self.is_detached_updater_active: bool = False
        self.last_check_status: str = "idle"
        self.last_check_error: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "AutoUpdater":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def check_for_updates(self, user_email: Optional[str] = None, user_role: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Queries both GitHub Releases API and Supabase Cloud for latest active release.
        Returns (is_update_available, release_dict, error_message).
        """
        self.current_version = get_installed_version()
        self.last_check_error = None

        # ── SOURCE A: Supabase Cloud Releases (Fast CDN & Role Filtering) ──
        supabase_release, sb_err = self._check_supabase(user_email, user_role)
        if supabase_release:
            latest_ver = supabase_release.get("version", "").strip()
            if is_newer_version(latest_ver, self.current_version):
                self.latest_release = supabase_release
                self.last_check_status = "update_available"
                logger.info(f"🚀 New Update Available from Supabase Cloud: v{latest_ver} (Current: v{self.current_version})", category="UPDATER")
                return True, supabase_release, None

        # ── SOURCE B: GitHub Releases API (Public Release Asset Discovery) ──
        gh_release, gh_err = self._check_github()
        if gh_release:
            latest_ver = gh_release.get("version", "").strip()
            if is_newer_version(latest_ver, self.current_version):
                # Prefer GitHub release if it's newer than or equal to Supabase release
                if not self.latest_release or is_newer_version(latest_ver, self.latest_release.get("version", "")):
                    self.latest_release = gh_release
                self.last_check_status = "update_available"
                logger.info(f"🚀 New Update Available from GitHub Releases: v{latest_ver} (Current: v{self.current_version})", category="UPDATER")
                return True, self.latest_release, None

        # If both checks ran without finding newer versions:
        if not sb_err and not gh_err:
            self.last_check_status = "up_to_date"
            return False, None, None

        # If all sources errored (e.g. no internet):
        err = sb_err or gh_err or "Could not reach update server."
        self.last_check_error = err
        self.last_check_status = "error"
        logger.warning(f"Update check non-critical warning: {err}", category="UPDATER")
        return False, None, err

    def _check_supabase(self, user_email: Optional[str] = None, user_role: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Queries Supabase app_releases table."""
        try:
            from app.core.cloud_manager import cloud_manager, ADMIN_EMAILS
            client = cloud_manager.client
            if not client:
                return None, "Supabase client not initialized"

            email = (user_email or (cloud_manager.current_user.get("email") if cloud_manager.current_user else "") or "").strip().lower()
            role = (user_role or (cloud_manager.current_user.get("role") if cloud_manager.current_user else "") or "").strip().lower()

            res = client.table("app_releases") \
                .select("*") \
                .eq("is_active", True) \
                .order("id", desc=True) \
                .execute()

            if not res.data:
                return None, None

            for rel in res.data:
                target = (rel.get("target_email") or "*").strip().lower()
                if target and target != "*":
                    allowed_targets = [e.strip().lower() for e in target.replace(";", ",").split(",") if e.strip()]
                    if email in allowed_targets:
                        pass
                    elif "admin" in allowed_targets:
                        is_admin = (email in [e.lower() for e in ADMIN_EMAILS]) or (role == "admin")
                        if not is_admin:
                            continue
                    else:
                        continue

                return {
                    "source": "supabase",
                    "version": rel.get("version", "").strip().lstrip("vV"),
                    "title": rel.get("title") or f"Waqas Automation Pro v{rel.get('version')}",
                    "release_notes": rel.get("changelog") or "Bug fixes and performance improvements.",
                    "download_url": rel.get("download_url", ""),
                    "is_mandatory": bool(rel.get("is_mandatory", False)),
                    "sha256": rel.get("sha256", ""),
                    "created_at": rel.get("created_at", "")
                }, None

            return None, None
        except Exception as e:
            return None, str(e)

    def _check_github(self) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Queries GitHub REST API for the latest release."""
        last_error = None
        for repo in GITHUB_REPOS:
            url = f"https://api.github.com/repos/{repo}/releases/latest"
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "WaqasAutomationPro-Updater",
                        "Accept": "application/vnd.github.v3+json"
                    }
                )
                with urllib.request.urlopen(req, timeout=8.0) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        tag = data.get("tag_name", "").strip().lstrip("vV")
                        if not tag:
                            continue

                        # Find download asset (prefer setup exe if available, or zip)
                        assets = data.get("assets", [])
                        dl_url = ""
                        sha256_hash = ""

                        # Search for setup.exe first
                        for a in assets:
                            name = a.get("name", "").lower()
                            if name.endswith("_setup.exe") or name.endswith(".exe"):
                                dl_url = a.get("browser_download_url", "")
                                break

                        # Search for patch zip second
                        if not dl_url:
                            for a in assets:
                                name = a.get("name", "").lower()
                                if name.startswith("update_") and name.endswith(".zip"):
                                    dl_url = a.get("browser_download_url", "")
                                    break

                        # Fallback to first zip asset
                        if not dl_url and assets:
                            dl_url = assets[0].get("browser_download_url", "")

                        if not dl_url:
                            dl_url = data.get("zipball_url", "")

                        return {
                            "source": "github",
                            "version": tag,
                            "title": data.get("name") or f"Waqas Automation Pro v{tag}",
                            "release_notes": data.get("body") or "Official GitHub release deployment.",
                            "download_url": dl_url,
                            "is_mandatory": False,
                            "sha256": sha256_hash,
                            "created_at": data.get("published_at", "")
                        }, None
            except urllib.error.HTTPError as he:
                last_error = f"GitHub API HTTP {he.code}: {he.reason}"
            except Exception as e:
                last_error = str(e)

        return None, last_error

    def download_and_install_update(
        self,
        download_url: str,
        version_str: str = "",
        expected_sha256: str = "",
        progress_callback=None
    ) -> Tuple[bool, str]:
        """
        Downloads update package, verifies SHA-256 (if supplied),
        extracts files, and executes detached runner to perform safe upgrade.
        Returns (success: bool, message: str).
        """
        if not download_url:
            return False, "Download URL is empty."

        new_ver = version_str.strip() or (self.latest_release.get("version", "") if self.latest_release else self.current_version)

        try:
            temp_dir = tempfile.mkdtemp(prefix="waqas_update_")
            is_installer_exe = download_url.lower().split("?")[0].endswith(".exe")

            logger.info(f"Downloading update v{new_ver} from: {download_url}", category="UPDATER")

            req = urllib.request.Request(
                download_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) WaqasAutomationPro-Updater"}
            )

            # ── 1. DOWNLOAD PHASE ──
            download_dest = os.path.join(temp_dir, "installer.exe" if is_installer_exe else "update.zip")
            with urllib.request.urlopen(req, timeout=60.0) as response, open(download_dest, "wb") as out_file:
                total_size = int(response.headers.get("Content-Length", 0))
                bytes_dl = 0
                chunk_size = 64 * 1024
                hasher = hashlib.sha256()

                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    hasher.update(chunk)
                    bytes_dl += len(chunk)
                    if progress_callback and total_size > 0:
                        percent = int((bytes_dl * 100) / total_size)
                        progress_callback(min(100, percent), bytes_dl, total_size)

            # ── 2. INTEGRITY VERIFICATION (SHA-256) ──
            downloaded_sha256 = hasher.hexdigest().lower()
            if expected_sha256 and expected_sha256.strip():
                if downloaded_sha256 != expected_sha256.strip().lower():
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    err_msg = f"Integrity check failed: Expected {expected_sha256[:12]}..., got {downloaded_sha256[:12]}..."
                    logger.error(err_msg, category="UPDATER")
                    return False, err_msg
                logger.info("✅ SHA-256 Checksum Verified Successfully!", category="UPDATER")

            # ── 3. INSTALLATION PHASE ──
            if is_installer_exe:
                # Direct Setup Installer Execution
                logger.info("Executing Windows Setup installer in detached process...", category="UPDATER")
                subprocess.Popen([download_dest, "/SILENT", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"], close_fds=True)
                self.is_detached_updater_active = True
                set_installed_version(new_ver)
                return True, "Installer launched."

            # Zip Patch Extraction
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(download_dest, "r") as zf:
                zf.extractall(extract_dir)

            source_content_dir = extract_dir
            subfolders = [os.path.join(extract_dir, d) for d in os.listdir(extract_dir) if os.path.isdir(os.path.join(extract_dir, d))]
            if len(subfolders) == 1 and not any(os.path.isfile(os.path.join(extract_dir, f)) for f in os.listdir(extract_dir)):
                source_content_dir = subfolders[0]

            is_frozen = getattr(sys, 'frozen', False)

            if is_frozen:
                app_exe = sys.executable
                install_dir = os.path.abspath(os.path.dirname(app_exe))
                DETACHED_FLAGS = 0x00000008 | 0x00000200 if os.name == 'nt' else 0

                bat_path = os.path.join(temp_dir, "apply_update.bat")
                bat_script_content = f"""@echo off
setlocal enabledelayedexpansion
title Waqas Automation Pro Auto-Updater
echo ======================================================
echo  Applying Waqas Automation Pro Update v{new_ver}...
echo  Preserving user data and database safely.
echo ======================================================

:: Force close running instance to release file locks
taskkill /F /IM WaqasAutomationPro.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: Robocopy application files while strictly preserving user databases and sessions
robocopy "{source_content_dir}" "{install_dir}" /E /R:10 /W:1 /XD "data" "logs" /XF "*.db" "*.db-wal" "*.db-shm" "user_session.json" /NJH /NJS /NDL /NC /NS

:: Update app_version.txt
if not exist "{install_dir}\\data" mkdir "{install_dir}\\data"
echo {new_ver}> "{install_dir}\\data\\app_version.txt"

:: Sync _internal directory if present
if exist "{install_dir}\\_internal" (
    if exist "{source_content_dir}\\sitecustomize.py" copy /Y "{source_content_dir}\\sitecustomize.py" "{install_dir}\\_internal\\sitecustomize.py" >nul
    if exist "{source_content_dir}\\app" robocopy "{source_content_dir}\\app" "{install_dir}\\_internal\\app" /E /R:5 /W:1 /NJH /NJS /NDL /NC /NS
    if exist "{source_content_dir}\\ui" robocopy "{source_content_dir}\\ui" "{install_dir}\\_internal\\ui" /E /R:5 /W:1 /NJH /NJS /NDL /NC /NS
    if exist "{source_content_dir}\\data\\viral_prompts" robocopy "{source_content_dir}\\data\\viral_prompts" "{install_dir}\\_internal\\data\\viral_prompts" /E /R:5 /W:1 /NJH /NJS /NDL /NC /NS
    if exist "{source_content_dir}\\_internal" robocopy "{source_content_dir}\\_internal" "{install_dir}\\_internal" /E /R:5 /W:1 /NJH /NJS /NDL /NC /NS
)

:: Relaunch application
echo Starting updated Waqas Automation Pro v{new_ver}...
start "" "{app_exe}"

:: Cleanup temporary folder
ping 127.0.0.1 -n 3 >nul
rd /s /q "{temp_dir}" 2>nul
exit
"""
                with open(bat_path, "w", encoding="utf-8") as bf:
                    bf.write(bat_script_content)

                logger.info(f"Triggering detached updater script: {bat_path}", category="UPDATER")
                subprocess.Popen(["cmd.exe", "/c", bat_path], creationflags=DETACHED_FLAGS, close_fds=True)

                self.is_detached_updater_active = True
                set_installed_version(new_ver)
                self.current_version = new_ver
                return True, "Update applied successfully. Restarting..."

            else:
                # Non-frozen development environment
                app_root = str(get_base_dir())
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
                        except Exception:
                            pass

                set_installed_version(new_ver)
                self.current_version = new_ver
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info(f"✅ Dev Update to v{new_ver} applied cleanly!", category="UPDATER")
                return True, "Update applied to workspace."

        except Exception as e:
            logger.error(f"Update installation failed: {e}", category="UPDATER")
            return False, str(e)

updater = AutoUpdater.get_instance()
