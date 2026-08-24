import os
import sys
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.cloud_manager import SUPABASE_URL, SUPABASE_KEY
from supabase import create_client

def main():
    base_dir = Path(__file__).resolve().parent.parent
    zip_path = base_dir / "update_v2.1.1.zip"

    print("[1/3] Packaging comprehensive update_v2.1.1.zip...")
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
        
        # 2. Version and sitecustomize files
        v_file = base_dir / "data" / "app_version.txt"
        if v_file.exists():
            zf.write(v_file, Path("data/app_version.txt"))
            zf.write(v_file, Path("_internal/data/app_version.txt"))

    print(f"Comprehensive Zip package created! Size: {zip_path.stat().st_size / 1024 / 1024:.2f} MB")

    print("[2/3] Uploading update_v2.1.1.zip to Supabase Storage...")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    with open(zip_path, "rb") as f:
        file_bytes = f.read()
        
    upload_res = client.storage.from_("releases").upload(
        path="update_v2.1.1.zip",
        file=file_bytes,
        file_options={"content-type": "application/zip", "upsert": "true"}
    )
    print("Storage upload response:", upload_res)

    print("[3/3] Updating app_releases table in Supabase...")
    public_url = f"{SUPABASE_URL}/storage/v1/object/public/releases/update_v2.1.1.zip"
    db_res = client.table("app_releases").update({
        "download_url": public_url,
        "is_active": True
    }).eq("version", "2.1.1").execute()

    print("Database updated:", len(db_res.data), "records")
    print(f"Download URL: {public_url}")
    print("SUCCESS: Comprehensive OTA Update Package is live on Supabase!")

if __name__ == "__main__":
    main()
