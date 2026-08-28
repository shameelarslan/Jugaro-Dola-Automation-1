"""
Publishes an OTA update through GitHub Releases instead of Supabase Storage.

GitHub hosts the file (unmetered bandwidth, permanent versioned URLs); the
Supabase app_releases table stays the control plane the app polls — this script
points its download_url at the GitHub asset. No app-side code depends on where
the file is hosted.

Usage:
    python scripts/publish_github_release.py                   # build patch zip, publish it
    python scripts/publish_github_release.py path\\to\\file      # publish an existing .zip or Setup .exe

Requirements:
    - GitHub CLI ('gh') installed and logged in to the account that owns
      RELEASES_REPO:  gh auth login
    - The version being released is RELEASE_VERSION in upload_release_zip.py
      (single source of truth, must equal CURRENT_VERSION in app/core/updater.py).

On first run it creates RELEASES_REPO as a PUBLIC repo — it must be public,
because installed apps download assets without authentication. Keep source code
out of it; it only holds release files.
"""

import sys
import shutil
import subprocess
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BASE_DIR / "scripts") not in sys.path:
    sys.path.insert(0, str(BASE_DIR / "scripts"))

from app.core.cloud_manager import SUPABASE_URL, SUPABASE_KEY
from supabase import create_client
from upload_release_zip import RELEASE_VERSION, build_zip

# Public repo that hosts release assets ONLY (no source code).
RELEASES_REPO = "abdiopp/waqas-automation-releases"

CHANGELOG = (
    "• Performance optimizations and stability improvements.\n"
    "• Updated Dola AI automation engine."
)

def _gh(*args, check=True):
    """Runs a GitHub CLI command and returns (returncode, stdout, stderr)."""
    res = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and res.returncode != 0:
        print(f"[ERROR] gh {' '.join(args[:3])}... failed:\n{res.stderr.strip()}")
        sys.exit(1)
    return res.returncode, res.stdout.strip(), res.stderr.strip()

def ensure_gh_ready():
    if not shutil.which("gh"):
        print("[ERROR] GitHub CLI ('gh') is not installed or not on PATH.")
        print("        Install from https://cli.github.com then run: gh auth login")
        sys.exit(1)
    code, _, err = _gh("auth", "status", check=False)
    if code != 0:
        print(f"[ERROR] GitHub CLI is not logged in:\n{err}")
        print("        Run: gh auth login")
        sys.exit(1)

def ensure_repo():
    code, out, _ = _gh("repo", "view", RELEASES_REPO, "--json", "visibility",
                       "--jq", ".visibility", check=False)
    if code != 0:
        print(f"[INFO] Creating public releases repo {RELEASES_REPO}...")
        _gh("repo", "create", RELEASES_REPO, "--public", "--add-readme",
            "--description", "Public OTA release assets for Waqas Automation Pro")
        print("  --> [OK] Repo created.")
    elif out.strip().upper() != "PUBLIC":
        print(f"[ERROR] {RELEASES_REPO} exists but is {out.strip()} — installed apps")
        print("        cannot download assets from a non-public repo. Make it public:")
        print(f"        gh repo edit {RELEASES_REPO} --visibility public --accept-visibility-change-consequences")
        sys.exit(1)

def publish_asset(file_path: Path) -> str:
    tag = f"v{RELEASE_VERSION}"
    code, _, _ = _gh("release", "view", tag, "--repo", RELEASES_REPO, check=False)
    if code != 0:
        print(f"[INFO] Creating release {tag} in {RELEASES_REPO}...")
        _gh("release", "create", tag, "--repo", RELEASES_REPO,
            "--title", tag, "--notes", CHANGELOG)
    print(f"[INFO] Uploading {file_path.name} ({file_path.stat().st_size / 1024 / 1024:.2f} MB)...")
    _gh("release", "upload", tag, str(file_path), "--repo", RELEASES_REPO, "--clobber")
    return f"https://github.com/{RELEASES_REPO}/releases/download/{tag}/{file_path.name}"

def verify_download(url: str, expected_size: int):
    """Confirms the asset is publicly downloadable (as the installed apps will)."""
    req = urllib.request.Request(url, method="HEAD",
                                 headers={"User-Agent": "WaqasAutomationPro-ReleaseCheck"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            size = int(res.headers.get("Content-Length", 0))
    except Exception as e:
        print(f"[ERROR] Public download check failed: {e}")
        print("        The app_releases table was NOT updated.")
        sys.exit(1)
    if size != expected_size:
        print(f"[ERROR] Size mismatch: uploaded {expected_size} bytes but URL serves {size}.")
        sys.exit(1)
    print(f"  --> [OK] Publicly downloadable ({size / 1024 / 1024:.2f} MB).")

def update_supabase(download_url: str):
    print(f"[INFO] Pointing app_releases v{RELEASE_VERSION} at GitHub...")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    row = {"download_url": download_url, "changelog": CHANGELOG, "is_active": True}
    res = supabase.table("app_releases").update(row).eq("version", RELEASE_VERSION).execute()
    if not res.data:
        row["version"] = RELEASE_VERSION
        supabase.table("app_releases").insert(row).execute()
        print("  --> [OK] New release row inserted.")
    else:
        print(f"  --> [OK] Existing release row updated ({len(res.data)} record).")

def main():
    ensure_gh_ready()

    if len(sys.argv) > 1:
        file_path = Path(sys.argv[1]).resolve()
        if not file_path.exists():
            print(f"[ERROR] File not found: {file_path}")
            sys.exit(1)
        if file_path.suffix.lower() not in (".zip", ".exe"):
            print("[ERROR] Only .zip patches or Setup .exe installers can be published.")
            sys.exit(1)
    else:
        file_path = build_zip()

    ensure_repo()
    url = publish_asset(file_path)
    verify_download(url, file_path.stat().st_size)
    update_supabase(url)

    print("\n" + "=" * 76)
    print(f"🚀 OTA UPDATE v{RELEASE_VERSION} IS LIVE VIA GITHUB RELEASES!")
    print(f"Download URL: {url}")
    print("=" * 76 + "\n")

if __name__ == "__main__":
    main()
