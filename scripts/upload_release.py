"""
Script to upload the installer to Supabase Cloud Storage (public 'releases' bucket).
"""

import os
import sys
from pathlib import Path
from supabase import create_client

SUPABASE_URL = "https://krdclqrlxbwpnadfxudd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtyZGNscXJseGJ3cG5hZGZ4dWRkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY4MjA5MDcsImV4cCI6MjEwMjM5NjkwN30.8W956EAIwjV_V43k5x7-SX7IsfTYoz_74HIMEJ9kwnQ"

INSTALLER_PATH = Path(r"c:\Users\I_T Computer\Antigravity\installer_output\WaqasAutomationPro_v2.0_Setup.exe")

def upload_installer():
    if not INSTALLER_PATH.exists():
        print(f"[ERROR] Installer file not found at: {INSTALLER_PATH}")
        sys.exit(1)

    file_size_mb = INSTALLER_PATH.stat().st_size / (1024 * 1024)
    print(f"[INFO] Connecting to Supabase Cloud...")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    remote_file_name = "WaqasAutomationPro_v2.0_Setup.exe"
    print(f"[INFO] Uploading {remote_file_name} ({file_size_mb:.2f} MB) to 'releases' bucket...")

    with open(INSTALLER_PATH, "rb") as f:
        file_bytes = f.read()

    # Upload or update (upsert)
    try:
        res = supabase.storage.from_("releases").upload(
            path=remote_file_name,
            file=file_bytes,
            file_options={"content-type": "application/x-msdownload", "upsert": "true"}
        )
        print(f"[SUCCESS] Upload complete: {res}")
    except Exception as e:
        print(f"[WARNING] Standard upload attempt returned: {e}")
        print("[INFO] Trying update/upsert alternative...")
        try:
            res = supabase.storage.from_("releases").update(
                path=remote_file_name,
                file=file_bytes,
                file_options={"content-type": "application/x-msdownload", "upsert": "true"}
            )
            print(f"[SUCCESS] Update complete: {res}")
        except Exception as e2:
            print(f"[ERROR] Failed to upload: {e2}")
            sys.exit(1)

    public_url = f"{SUPABASE_URL}/storage/v1/object/public/releases/{remote_file_name}"
    print("\n" + "=" * 70)
    print("🚀 PUBLIC DIRECT DOWNLOAD URL:")
    print(public_url)
    print("=" * 70 + "\n")

    # Also update app_releases table if present
    try:
        supabase.table("app_releases").upsert({
            "version": "2.0.0",
            "download_url": public_url,
            "release_notes": "Official v2.0 Commercial Release with Multi-User SaaS & Cloud Security.",
            "is_active": True
        }).execute()
        print("[INFO] Synced with 'app_releases' table for auto-updater.")
    except Exception as e:
        print(f"[NOTE] app_releases table update notice: {e}")

if __name__ == "__main__":
    upload_installer()
