"""
Creates and publishes an Auto-Update Patch (v2.0.3) directly to Supabase Cloud.
Equipped with sitecustomize.py disk-priority hook so all existing v2.0.0/v2.0.1/v2.0.2 installations
immediately execute the updated code on restart!
"""

import os
import sys
import zipfile
import requests
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(r"c:\Users\I_T Computer\Antigravity")
APP_DIR = ROOT_DIR / "app"
VERSION_STR = "2.0.3"
PATCH_ZIP = ROOT_DIR / "installer_output" / f"update_v{VERSION_STR}.zip"
SITECUSTOMIZE_FILE = ROOT_DIR / "sitecustomize.py"

SUPABASE_URL = "https://krdclqrlxbwpnadfxudd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtyZGNscXJseGJ3cG5hZGZ4dWRkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY4MjA5MDcsImV4cCI6MjEwMjM5NjkwN30.8W956EAIwjV_V43k5x7-SX7IsfTYoz_74HIMEJ9kwnQ"

def build_patch_zip():
    print(f"[1/3] Packaging 'app/' directory and runtime hooks into {PATCH_ZIP.name}...", flush=True)
    PATCH_ZIP.parent.mkdir(parents=True, exist_ok=True)

    # Ensure sitecustomize.py exists
    sitecustomize_code = '''"""
Dynamic Runtime Hotfix & Disk-Priority Module Loader for Waqas Automation Pro.
Enables PyInstaller to prioritize updated disk modules in _internal/app over frozen PYZ bytecode.
"""
import sys
import os
from pathlib import Path

try:
    internal_dir = os.path.abspath(os.path.dirname(__file__))
    if internal_dir not in sys.path:
        sys.path.insert(0, internal_dir)

    app_dir = os.path.join(internal_dir, "app")
    if os.path.exists(app_dir):
        class DiskPriorityFinder:
            def find_spec(self, fullname, path, target=None):
                if fullname == "app" or fullname.startswith("app."):
                    # Delegate to standard PathFinder to load from disk
                    for finder in sys.meta_path:
                        if finder is not self and hasattr(finder, 'find_spec') and 'PathFinder' in finder.__class__.__name__:
                            try:
                                spec = finder.find_spec(fullname, path, target)
                                if spec is not None:
                                    return spec
                            except Exception:
                                pass
                return None

        # Insert at the very top of meta_path so it takes precedence over FrozenImporter
        sys.meta_path.insert(0, DiskPriorityFinder())
except Exception as _e:
    pass
'''
    SITECUSTOMIZE_FILE.write_text(sitecustomize_code, encoding="utf-8")

    with zipfile.ZipFile(PATCH_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        # Write sitecustomize.py at root of zip
        zf.write(SITECUSTOMIZE_FILE, arcname="sitecustomize.py")
        
        # Also write version file
        version_data = f"{VERSION_STR}\n"
        zf.writestr("data/app_version.txt", version_data)

        # Write all app files
        for root, dirs, files in os.walk(APP_DIR):
            if "__pycache__" in root:
                continue
            for f in files:
                if f.endswith((".pyc", ".pyo")):
                    continue
                file_path = Path(root) / f
                arc_name = Path("app") / file_path.relative_to(APP_DIR)
                zf.write(file_path, arcname=str(arc_name))
                
    size_mb = PATCH_ZIP.stat().st_size / (1024 * 1024)
    print(f"  --> Patch Zip created successfully ({size_mb:.2f} MB / {PATCH_ZIP.stat().st_size / 1024:.1f} KB)", flush=True)

def upload_patch_to_cloud():
    print(f"[2/3] Uploading {PATCH_ZIP.name} to Supabase Storage ('releases' bucket)...", flush=True)
    
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
        "x-upsert": "true",
        "Content-Type": "application/zip"
    }

    url = f"{SUPABASE_URL}/storage/v1/object/releases/{PATCH_ZIP.name}"
    with open(PATCH_ZIP, "rb") as f:
        res = requests.post(url, headers=headers, data=f, timeout=120)

    if res.status_code in (200, 201):
        public_download_url = f"{SUPABASE_URL}/storage/v1/object/public/releases/{PATCH_ZIP.name}"
        print(f"  --> [OK] Upload complete: {public_download_url}", flush=True)
        return public_download_url
    else:
        print(f"  --> [ERROR] Upload failed: {res.status_code} {res.text}", flush=True)
        return None

def sync_supabase_release(download_url: str):
    print(f"[3/3] Publishing v{VERSION_STR} release to Cloud Database...", flush=True)
    from supabase import create_client
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    changelog_text = (
        "• 500+ Bulk Prompts Support (Zero Lag & Instant Import Engine)\n"
        "• Complete Prompt Deletion on 'Clear Completed'\n"
        "• Ultra-Fast Tab Switching (< 10ms instantaneous response)\n"
        "• Custom Output Download Folder Persistence & Selection Confirmation\n"
        "• First-Time Interactive Onboarding Tutorial & Step-by-Step Guide\n"
        "• Dashboard Active Session Controls: Inspect (Open) & Terminate (Close)\n"
        "• Per-Session 15 Videos Left Quota Tracking & Auto-Expiration\n"
        "• 100% User Session & Saved Data Preservation Guarantee"
    )

    # Deactivate older releases
    try:
        sb.table("app_releases").update({"is_active": False}).execute()
    except Exception:
        pass

    # Insert / Upsert v2.0.3
    res = sb.table("app_releases").upsert({
        "version": VERSION_STR,
        "download_url": download_url,
        "is_active": True,
        "changelog": changelog_text
    }).execute()
    
    print("\n" + "=" * 76, flush=True)
    print(f"🚀 AUTO-UPDATE PATCH v{VERSION_STR} IS LIVE ON CLOUD!", flush=True)
    print("=" * 76, flush=True)
    print(f"Patch Download URL: {download_url}", flush=True)
    print(f"When users on v2.0.0, v2.0.1, or v2.0.2 open their software, it will prompt to Auto-Update to v{VERSION_STR}!", flush=True)
    print("=" * 76 + "\n", flush=True)

if __name__ == "__main__":
    build_patch_zip()
    dl_url = upload_patch_to_cloud()
    if dl_url:
        sync_supabase_release(dl_url)
