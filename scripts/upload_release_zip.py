import os
import sys
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.cloud_manager import SUPABASE_URL, SUPABASE_KEY
from supabase import create_client

# The version being released. MUST match the row in the app_releases table
# and should equal CURRENT_VERSION in app/core/updater.py at build time.
RELEASE_VERSION = "2.1.1"

def main():
    base_dir = Path(__file__).resolve().parent.parent
    zip_path = base_dir / f"update_v{RELEASE_VERSION}.zip"

    print(f"[1/3] Packaging comprehensive update_v{RELEASE_VERSION}.zip...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Base folders
        for folder in ["app", "ui", "data/viral_prompts"]:
            src_folder = base_dir / folder
            if src_folder.exists():
                for root, dirs, files in os.walk(src_folder):
                    dirs[:] = [d for d in dirs if d != "__pycache__"]
                    for file in files:
                        if file.endswith(".pyc"):
                            continue
                        full_p = Path(root) / file
                        rel_p = full_p.relative_to(base_dir)
                        # Write to root path in zip
                        zf.write(full_p, rel_p)
                        # ALSO write to _internal/ path in zip for PyInstaller installations!
                        zf.write(full_p, Path("_internal") / rel_p)
        
        # 2. Version stamp — always the RELEASE version, never the local
        # data/app_version.txt (which still holds the PREVIOUS version on the
        # build machine and caused installed apps to re-prompt the same update forever).
        zf.writestr("data/app_version.txt", RELEASE_VERSION)
        zf.writestr("_internal/data/app_version.txt", RELEASE_VERSION)

        # 3. sitecustomize disk-priority hook
        sc_file = base_dir / "sitecustomize.py"
        if sc_file.exists():
            zf.write(sc_file, Path("sitecustomize.py"))
            zf.write(sc_file, Path("_internal/sitecustomize.py"))

    print(f"Comprehensive Zip package created! Size: {zip_path.stat().st_size / 1024 / 1024:.2f} MB")

    print(f"[2/3] Uploading update_v{RELEASE_VERSION}.zip to Supabase Storage...")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    with open(zip_path, "rb") as f:
        file_bytes = f.read()
        
    upload_res = client.storage.from_("releases").upload(
        path=f"update_v{RELEASE_VERSION}.zip",
        file=file_bytes,
        file_options={"content-type": "application/zip", "upsert": "true"}
    )
    print("Storage upload response:", upload_res)

    print("[3/3] Updating app_releases table in Supabase...")
    public_url = f"{SUPABASE_URL}/storage/v1/object/public/releases/update_v{RELEASE_VERSION}.zip"
    db_res = client.table("app_releases").update({
        "download_url": public_url,
        "is_active": True
    }).eq("version", RELEASE_VERSION).execute()

    print("Database updated:", len(db_res.data), "records")
    print(f"Download URL: {public_url}")
    print("SUCCESS: Comprehensive OTA Update Package is live on Supabase!")

if __name__ == "__main__":
    main()
