"""
Uploads a full Setup installer (.exe) to Supabase Cloud Storage (public 'releases'
bucket) and publishes it in the app_releases table.

Use this for FULL releases (new dependencies, Python bump, exe/bootstrap changes).
For Python-code-only hot-patches use upload_release_zip.py instead.

Usage:
    python scripts/upload_release.py                # uses installer_output/WaqasAutomationPro_v<VER>_Setup.exe
    python scripts/upload_release.py path\\to\\Setup.exe

NOTE: the auto-updater treats a download_url ending in .exe as a standalone
installer and executes it, instead of applying a zip patch.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.cloud_manager import SUPABASE_URL, SUPABASE_KEY
from supabase import create_client

# The version being released. MUST equal CURRENT_VERSION in app/core/updater.py
# at build time so freshly installed apps don't immediately re-prompt.
RELEASE_VERSION = "2.1.1"

CHANGELOG = (
    "• Performance optimizations and stability improvements.\n"
    "• Updated Dola AI automation engine."
)

def upload_installer():
    if len(sys.argv) > 1:
        installer_path = Path(sys.argv[1])
    else:
        installer_path = BASE_DIR / "installer_output" / f"WaqasAutomationPro_v{RELEASE_VERSION}_Setup.exe"

    if not installer_path.exists():
        print(f"[ERROR] Installer file not found at: {installer_path}")
        print("        Build it first (build_installer.bat) or pass the path as an argument.")
        sys.exit(1)

    file_size_mb = installer_path.stat().st_size / (1024 * 1024)
    print("[1/3] Connecting to Supabase Cloud...")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    remote_file_name = f"WaqasAutomationPro_v{RELEASE_VERSION}_Setup.exe"
    print(f"[2/3] Uploading {remote_file_name} ({file_size_mb:.2f} MB) to 'releases' bucket...")

    with open(installer_path, "rb") as f:
        file_bytes = f.read()

    try:
        res = supabase.storage.from_("releases").upload(
            path=remote_file_name,
            file=file_bytes,
            file_options={"content-type": "application/x-msdownload", "upsert": "true"}
        )
        print(f"  --> [OK] Upload complete: {res}")
    except Exception as e:
        print(f"[WARNING] Standard upload attempt returned: {e}")
        print("[INFO] Trying update/upsert alternative...")
        try:
            res = supabase.storage.from_("releases").update(
                path=remote_file_name,
                file=file_bytes,
                file_options={"content-type": "application/x-msdownload", "upsert": "true"}
            )
            print(f"  --> [OK] Update complete: {res}")
        except Exception as e2:
            print(f"[ERROR] Failed to upload: {e2}")
            sys.exit(1)

    public_url = f"{SUPABASE_URL}/storage/v1/object/public/releases/{remote_file_name}"
    print("\n" + "=" * 70)
    print("🚀 PUBLIC DIRECT DOWNLOAD URL:")
    print(public_url)
    print("=" * 70 + "\n")

    print(f"[3/3] Publishing v{RELEASE_VERSION} in the app_releases table...")
    try:
        # The auto-updater reads the 'changelog' column (not 'release_notes').
        row = {
            "download_url": public_url,
            "changelog": CHANGELOG,
            "is_active": True
        }
        res = supabase.table("app_releases").update(row).eq("version", RELEASE_VERSION).execute()
        if not res.data:
            row["version"] = RELEASE_VERSION
            supabase.table("app_releases").insert(row).execute()
            print("  --> [OK] New release row inserted.")
        else:
            print(f"  --> [OK] Existing release row updated ({len(res.data)} record).")
        print(f"SUCCESS: Full installer release v{RELEASE_VERSION} is live on Supabase!")
    except Exception as e:
        print(f"[ERROR] app_releases table update failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    upload_installer()
