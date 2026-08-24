"""
Standalone Compilation Script for Waqas Automation Pro v2.0.
Compiles the application into a self-contained portable distribution.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
GUI_ASSETS_DIR = ROOT_DIR / "app" / "gui" / "assets"

def clean_build_artifacts():
    print("[1/3] Cleaning previous build artifacts...")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR, ignore_errors=True)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR, ignore_errors=True)

def ensure_icon_exists():
    logo_png = GUI_ASSETS_DIR / "logo.png"
    logo_ico = GUI_ASSETS_DIR / "logo.ico"
    if logo_png.exists() and not logo_ico.exists():
        try:
            from PIL import Image
            img = Image.open(str(logo_png))
            img.save(str(logo_ico), format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
            print("[INFO] Generated logo.ico from logo.png")
        except Exception as e:
            print(f"[WARNING] Could not generate .ico from .png: {e}")
    return logo_ico if logo_ico.exists() else None

def build_executable():
    clean_build_artifacts()
    print("[2/3] Compiling Waqas Automation Pro with PyInstaller...")

    logo_ico = ensure_icon_exists()
    icon_arg = [f"--icon={logo_ico}"] if logo_ico else []

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=WaqasAutomationPro",
        f"--add-data={GUI_ASSETS_DIR};app/gui/assets",
        "--collect-all=app",
        "--collect-all=playwright",
        "--collect-all=supabase",
        "--collect-all=postgrest",
        "--collect-all=gotrue",
        "--collect-all=realtime",
        "--collect-all=storage3",
        "--hidden-import=config",
        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=packaging",
        "--hidden-import=packaging.version",
        "--hidden-import=sqlite3",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        str(ROOT_DIR / "main.py")
    ] + icon_arg

    subprocess.check_call(cmd, cwd=str(ROOT_DIR))
    print("[3/3] PyInstaller build completed successfully!")

if __name__ == "__main__":
    build_executable()
