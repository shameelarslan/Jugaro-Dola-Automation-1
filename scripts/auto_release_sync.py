"""
Automatic GitHub Release → Supabase Sync Script
Detects new releases on GitHub and auto-pushes them to Supabase app_releases table.
Run this periodically (cron job or manual) to keep releases in sync.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.cloud_manager import cloud_manager
from app.core.logger import logger

GITHUB_REPO = "shameelarslan/Jugaro-Dola-Automation-1"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases"

# Admin emails who get auto-update access
ADMIN_EMAILS = [
    "shameelarslanali786@gmail.com",
    # Add more admin emails here
]

def fetch_github_releases() -> List[Dict[str, Any]]:
    """Fetch all releases from GitHub API."""
    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={"User-Agent": "WaqasAutomationPro/2.1.3"}
        )
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"Failed to fetch GitHub releases: {e}", category="RELEASE_SYNC")
        return []

def parse_release_info(gh_release: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract relevant info from GitHub release JSON."""
    try:
        version = gh_release.get("tag_name", "").replace("v", "").strip()
        if not version:
            return None

        # Find MSI or EXE asset
        download_url = None
        for asset in gh_release.get("assets", []):
            name = asset.get("name", "").lower()
            if ".msi" in name or "setup.exe" in name:
                download_url = asset.get("browser_download_url")
                break

        if not download_url:
            logger.warning(f"No installer found for release {version}", category="RELEASE_SYNC")
            return None

        # Extract changelog from body
        changelog = gh_release.get("body", "")
        if not changelog:
            changelog = f"Version {version} - Automated build from GitHub"

        # Detect if mandatory (e.g., has "BREAKING" or "CRITICAL" in title)
        title = gh_release.get("name", "").upper()
        is_mandatory = "BREAKING" in title or "CRITICAL" in title

        return {
            "version": version,
            "download_url": download_url,
            "changelog": changelog[:500],  # Limit to 500 chars
            "is_mandatory": is_mandatory,
            "published_at": gh_release.get("published_at"),
        }
    except Exception as e:
        logger.error(f"Error parsing release info: {e}", category="RELEASE_SYNC")
        return None

def release_exists_in_supabase(version: str) -> bool:
    """Check if version already exists in Supabase."""
    try:
        client = cloud_manager.client
        if not client:
            return False

        res = client.table("app_releases") \
            .select("id") \
            .eq("version", version) \
            .execute()

        return len(res.data) > 0
    except Exception as e:
        logger.warning(f"Error checking Supabase: {e}", category="RELEASE_SYNC")
        return False

def sync_release_to_supabase(release_info: Dict[str, Any]) -> bool:
    """Insert or update release in Supabase."""
    try:
        client = cloud_manager.client
        if not client:
            logger.error("Cloud manager not initialized", category="RELEASE_SYNC")
            return False

        target_emails = ",".join(ADMIN_EMAILS)

        # Check if already exists
        if release_exists_in_supabase(release_info["version"]):
            # Update existing (only use safe columns)
            res = client.table("app_releases") \
                .update({
                    "download_url": release_info["download_url"],
                    "changelog": release_info["changelog"],
                    "is_mandatory": release_info["is_mandatory"],
                    "is_active": True,
                    "target_email": target_emails,
                }) \
                .eq("version", release_info["version"]) \
                .execute()
            logger.info(f"✅ Updated release v{release_info['version']} in Supabase", category="RELEASE_SYNC")
        else:
            # Insert new (only use safe columns)
            res = client.table("app_releases") \
                .insert({
                    "version": release_info["version"],
                    "download_url": release_info["download_url"],
                    "changelog": release_info["changelog"],
                    "is_mandatory": release_info["is_mandatory"],
                    "is_active": True,
                    "target_email": target_emails,
                }) \
                .execute()
            logger.info(f"✅ Created release v{release_info['version']} in Supabase", category="RELEASE_SYNC")

        return True
    except Exception as e:
        logger.error(f"Failed to sync release to Supabase: {e}", category="RELEASE_SYNC")
        return False

def run_sync():
    """Main sync function."""
    logger.info("🔄 Starting GitHub → Supabase release sync...", category="RELEASE_SYNC")

    # Fetch latest releases from GitHub
    releases = fetch_github_releases()
    if not releases:
        logger.warning("No releases found on GitHub", category="RELEASE_SYNC")
        return

    logger.info(f"Found {len(releases)} releases on GitHub", category="RELEASE_SYNC")

    synced_count = 0
    for gh_release in releases:
        # Skip drafts and pre-releases
        if gh_release.get("draft") or gh_release.get("prerelease"):
            continue

        release_info = parse_release_info(gh_release)
        if not release_info:
            continue

        if sync_release_to_supabase(release_info):
            synced_count += 1

    logger.info(f"✅ Sync complete! {synced_count} releases synced to Supabase", category="RELEASE_SYNC")

if __name__ == "__main__":
    run_sync()
