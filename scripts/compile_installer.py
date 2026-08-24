"""
Compiles Inno Setup installer script for Waqas Automation Pro v2.0.
Locates ISCC.exe on the system and produces the final Windows Installer.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
ISS_SCRIPT = ROOT_DIR / "scripts" / "installer_config.iss"
OUTPUT_DIR = ROOT_DIR / "installer_output"
VERSION_FILE = ROOT_DIR / "data" / "app_version.txt"

def get_current_version() -> str:
    if VERSION_FILE.exists():
        try:
            v = VERSION_FILE.read_text(encoding="utf-8").strip()
            if v:
                return v
        except Exception:
            pass
    return "2.0.7"

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

    # Check PATH
    iscc_in_path = shutil.which("iscc") or shutil.which("ISCC")
    if iscc_in_path:
        return iscc_in_path

    return ""

def compile_installer():
    iscc_exe = find_iscc()
    if not iscc_exe:
        print("[ERROR] Inno Setup compiler (ISCC.exe) was not found on this system.")
        print("Please install Inno Setup from https://jrsoftware.org/isdl.php")
        sys.exit(1)

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
        print("\n" + "=" * 64)
        print("[SUCCESS] Production Windows Installer generated successfully!")
        print(f"File Path: {output_exe}")
        print(f"File Size: {size_mb:.2f} MB")
        print("=" * 64 + "\n")
    else:
        print(f"[WARNING] Setup executable was not found at expected path: {output_exe}")

if __name__ == "__main__":
    compile_installer()
