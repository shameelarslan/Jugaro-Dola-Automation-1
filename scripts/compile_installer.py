"""
Compiles Inno Setup installer script for Waqas Automation Pro.
Automatically synchronizes latest workspace assets into dist, builds installer,
computes SHA-256 checksums, and produces release manifest.
"""

import os
import sys
import json
import shutil
import hashlib
import datetime
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
ISS_SCRIPT = ROOT_DIR / "scripts" / "installer_config.iss"
OUTPUT_DIR = ROOT_DIR / "installer_output"
DIST_DIR = ROOT_DIR / "dist" / "WaqasAutomationPro"

def get_current_version() -> str:
    from app.core.version import get_installed_version
    return get_installed_version()

def find_iscc() -> str:
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 7\ISCC.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
        r"C:\Program Files\Inno Setup 7\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 7\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c

    iscc_in_path = shutil.which("iscc") or shutil.which("ISCC")
    if iscc_in_path:
        return iscc_in_path

    return ""

def sync_assets_to_dist():
    """Ensures dist directory has latest UI, app code, and version file."""
    if not DIST_DIR.exists():
        print(f"[WARNING] Dist directory not found at {DIST_DIR}. PyInstaller build may be needed.")
        return

    print("[INFO] Synchronizing latest workspace code and UI into dist package...")
    ui_src = ROOT_DIR / "ui"
    app_src = ROOT_DIR / "app"
    sitecust_src = ROOT_DIR / "sitecustomize.py"
    ver_src = ROOT_DIR / "data" / "app_version.txt"

    # Sync UI
    if ui_src.exists():
        for target in [DIST_DIR / "ui", DIST_DIR / "_internal" / "ui"]:
            target.mkdir(parents=True, exist_ok=True)
            for item in ui_src.glob("**/*"):
                if item.is_file():
                    rel = item.relative_to(ui_src)
                    dest = target / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)

    # Sync App
    if app_src.exists():
        target_app = DIST_DIR / "_internal" / "app"
        target_app.mkdir(parents=True, exist_ok=True)
        for item in app_src.glob("**/*"):
            if item.is_file() and not item.name.endswith((".pyc", ".pyo")) and "__pycache__" not in str(item):
                rel = item.relative_to(app_src)
                dest = target_app / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest)

    # Sync sitecustomize
    if sitecust_src.exists():
        for target in [DIST_DIR / "sitecustomize.py", DIST_DIR / "_internal" / "sitecustomize.py"]:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sitecust_src, target)

    # Sync app_version.txt
    if ver_src.exists():
        for target in [DIST_DIR / "data" / "app_version.txt", DIST_DIR / "_internal" / "data" / "app_version.txt"]:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ver_src, target)

def compute_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def compile_installer():
    iscc_exe = find_iscc()
    if not iscc_exe:
        print("[ERROR] Inno Setup compiler (ISCC.exe) was not found on this system.")
        print("Please install Inno Setup from https://jrsoftware.org/isdl.php")
        sys.exit(1)

    sync_assets_to_dist()

    version_str = get_current_version()
    output_filename = f"WaqasAutomationPro_v{version_str}_Setup.exe"
    output_exe = OUTPUT_DIR / output_filename

    print(f"[INFO] Found Inno Setup Compiler: {iscc_exe}")
    print(f"[INFO] Building Installer for Version: v{version_str}")
    print(f"[INFO] Output Target: {output_filename}")
    print(f"[INFO] Compiling installer from: {ISS_SCRIPT}")
    
    cmd = [
        iscc_exe,
        f"/DMyAppVersion={version_str}",
        f"/DOutputBaseFilename=WaqasAutomationPro_v{version_str}_Setup",
        str(ISS_SCRIPT)
    ]
    result = subprocess.run(cmd, cwd=str(ROOT_DIR))
    
    if result.returncode != 0:
        print(f"[ERROR] Inno Setup compilation failed with exit code {result.returncode}")
        sys.exit(result.returncode)

    if output_exe.exists():
        size_mb = output_exe.stat().st_size / (1024 * 1024)
        checksum = compute_sha256(output_exe)

        # Generate Release Manifest JSON
        manifest_data = {
            "version": version_str,
            "release_title": f"Waqas Automation Pro v{version_str}",
            "release_date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "installer_filename": output_filename,
            "installer_size_mb": round(size_mb, 2),
            "sha256": checksum,
            "mandatory": False,
            "release_notes": [
                f"Waqas Automation Pro v{version_str} Production Release",
                "New Admin Testing & Leads Generation Engine",
                "Automated Schema Migration & Data Preservation System",
                "Performance & Stability Enhancements"
            ]
        }
        manifest_file = OUTPUT_DIR / f"release_manifest_v{version_str}.json"
        manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        print("\n" + "=" * 68)
        print("[SUCCESS] Production Windows Installer generated successfully!")
        print(f"File Path:  {output_exe}")
        print(f"File Size:  {size_mb:.2f} MB")
        print(f"SHA-256:    {checksum}")
        print(f"Manifest:   {manifest_file}")
        print("=" * 68 + "\n")
    else:
        print(f"[WARNING] Setup executable was not found at expected path: {output_exe}")

if __name__ == "__main__":
    compile_installer()
