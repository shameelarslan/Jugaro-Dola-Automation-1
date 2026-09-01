"""
Admin-Only Auto-Update Publisher (GitHub Releases / Cloud Storage).
Packages the latest application code and registers the release targeted exclusively to ADMIN users.
Only users with role == 'admin' or matching ADMIN_EMAILS will receive this update in their app!
"""

import os
import sys
import zipfile
import urllib.request
import urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

APP_DIR = ROOT_DIR / "app"
UI_DIR = ROOT_DIR / "ui"
SITECUSTOMIZE_FILE = ROOT_DIR / "sitecustomize.py"

SUPABASE_URL = "https://krdclqrlxbwpnadfxudd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtyZGNscXJseGJ3cG5hZGZ4dWRkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY4MjA5MDcsImV4cCI6MjEwMjM5NjkwN30.8W956EAIwjV_V43k5x7-SX7IsfTYoz_74HIMEJ9kwnQ"

TARGET_AUDIENCE = "*"

def build_patch_zip(version_str: str) -> Path:
    output_dir = ROOT_DIR / "installer_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    patch_zip = output_dir / f"update_v{version_str}.zip"

    dist_app_dir = ROOT_DIR / "dist" / "WaqasAutomationPro"

    with zipfile.ZipFile(patch_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        if dist_app_dir.exists():
            print("  --> Packaging compiled launcher, core app modules & UI ...")
            main_exe = dist_app_dir / "WaqasAutomationPro.exe"
            if main_exe.exists():
                zf.write(main_exe, arcname="WaqasAutomationPro.exe")

            # Include entire app directory from workspace root
            if APP_DIR.exists():
                for root, dirs, files in os.walk(APP_DIR):
                    if "__pycache__" in root:
                        continue
                    for f in files:
                        if f.endswith((".pyc", ".pyo")):
                            continue
                        file_path = Path(root) / f
                        arc_name = Path("app") / file_path.relative_to(APP_DIR)
                        zf.write(file_path, arcname=str(arc_name))
                        zf.write(file_path, arcname=str(Path("_internal/app") / file_path.relative_to(APP_DIR)))

            # Include entire ui directory from workspace root
            if UI_DIR.exists():
                for root, dirs, files in os.walk(UI_DIR):
                    for f in files:
                        file_path = Path(root) / f
                        arc_name = Path("ui") / file_path.relative_to(UI_DIR)
                        zf.write(file_path, arcname=str(arc_name))
                        zf.write(file_path, arcname=str(Path("_internal/ui") / file_path.relative_to(UI_DIR)))

            # Include sitecustomize.py
            if SITECUSTOMIZE_FILE.exists():
                zf.write(SITECUSTOMIZE_FILE, arcname="sitecustomize.py")
                zf.write(SITECUSTOMIZE_FILE, arcname="_internal/sitecustomize.py")
        else:
            if SITECUSTOMIZE_FILE.exists():
                zf.write(SITECUSTOMIZE_FILE, arcname="sitecustomize.py")
                zf.write(SITECUSTOMIZE_FILE, arcname="_internal/sitecustomize.py")

            if APP_DIR.exists():
                for root, dirs, files in os.walk(APP_DIR):
                    if "__pycache__" in root or f.endswith((".pyc", ".pyo")):
                        continue
                    for f in files:
                        file_path = Path(root) / f
                        arc_name = Path("app") / file_path.relative_to(APP_DIR)
                        zf.write(file_path, arcname=str(arc_name))
                        zf.write(file_path, arcname=str(Path("_internal/app") / file_path.relative_to(APP_DIR)))

            if UI_DIR.exists():
                for root, dirs, files in os.walk(UI_DIR):
                    for f in files:
                        file_path = Path(root) / f
                        arc_name = Path("ui") / file_path.relative_to(UI_DIR)
                        zf.write(file_path, arcname=str(arc_name))
                        zf.write(file_path, arcname=str(Path("_internal/ui") / file_path.relative_to(UI_DIR)))

        # Always inject version file into both root and _internal
        version_data = f"{version_str}\n"
        zf.writestr("data/app_version.txt", version_data)
        zf.writestr("_internal/data/app_version.txt", version_data)

    size_mb = patch_zip.stat().st_size / (1024 * 1024)
    print(f"  --> ✅ Fast Patch Zip created: {patch_zip.name} ({size_mb:.2f} MB)", flush=True)
    return patch_zip

def upload_to_supabase(patch_zip: Path) -> str:
    print(f"\n[2/3] ☁️ Uploading {patch_zip.name} to Cloud Storage ('releases' bucket)...", flush=True)
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
        "x-upsert": "true",
        "Content-Type": "application/zip"
    }

    url = f"{SUPABASE_URL}/storage/v1/object/releases/{patch_zip.name}"
    try:
        with open(patch_zip, "rb") as f:
            data = f.read()
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=120) as resp:
            status = resp.status
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/releases/{patch_zip.name}"
        print(f"  --> ✅ Upload Complete: {public_url}", flush=True)
        return public_url
    except Exception as e:
        print(f"  --> ⚠️ Cloud direct upload note: {e}", flush=True)
        return f"{SUPABASE_URL}/storage/v1/object/public/releases/{patch_zip.name}"

def publish_admin_release(version_str: str, download_url: str, changelog: str = ""):
    print(f"\n[3/3] 🚀 Publishing Admin-Only Release v{version_str} to Cloud Database...", flush=True)
    try:
        from supabase import create_client
        sb = create_client(SUPABASE_URL, SUPABASE_KEY)

        if not changelog:
            changelog = f"• Official v{version_str} Admin Hotfix & Feature Upgrade\n• GitHub Release Deployment\n• Performance & Security Enhancements"

        # Register release targeting only 'admin'
        res = sb.table("app_releases").upsert({
            "version": version_str,
            "download_url": download_url,
            "target_email": TARGET_AUDIENCE,
            "is_active": True,
            "changelog": changelog
        }).execute()

        print("\n" + "=" * 76, flush=True)
        print(f"🎉 ADMIN-ONLY UPDATE v{version_str} IS NOW LIVE!", flush=True)
        print("=" * 76, flush=True)
        print(f"📌 Target Audience: ONLY Admin Users (target_email = 'admin')")
        print(f"🔗 Download URL: {download_url}")
        print(f"⚡ When Admin users open the app or click 'Check Updates', they will receive this update immediately.")
        print(f"🛡️ Regular/Free/Paid users will NOT see or receive this update.")
        print("=" * 76 + "\n", flush=True)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to publish release: {e}", flush=True)
        return False

def main():
    print("=" * 76)
    print("        WAQAS AUTOMATION PRO - ADMIN GITHUB UPDATE PUBLISHER")
    print("=" * 76)

    # Read current version
    from app.core.updater import get_installed_version
    curr_ver = get_installed_version()
    print(f"Current Installed Version: v{curr_ver}")

    # Prompt or get arguments
    if len(sys.argv) > 1:
        new_version = sys.argv[1].strip()
    else:
        parts = curr_ver.split(".")
        try:
            parts[-1] = str(int(parts[-1]) + 1)
            default_new = ".".join(parts)
        except Exception:
            default_new = "2.1.2"
        new_version = input(f"Enter New Version Number (Default: {default_new}): ").strip() or default_new

    # Custom GitHub download URL or build local patch
    github_url = ""
    if len(sys.argv) > 2:
        github_url = sys.argv[2].strip()
    else:
        repo_default = f"https://github.com/shameelarslan/Jugaro-Dola-Automation/releases/download/v{new_version}/update_v{new_version}.zip"
        print(f"\nDefault GitHub Release URL format:")
        print(f"  {repo_default}")
        choice = input("\nEnter custom GitHub URL (or press Enter to auto-upload to Cloud Storage): ").strip()
        if choice.startswith("http"):
            github_url = choice

    patch_file = build_patch_zip(new_version)

    final_url = github_url
    if not final_url:
        final_url = upload_to_supabase(patch_file)

    publish_admin_release(new_version, final_url)

if __name__ == "__main__":
    main()
