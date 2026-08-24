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

    ui_dir = ROOT_DIR / "ui"
    data_dir = ROOT_DIR / "data"

    add_data_args = [
        f"--add-data={GUI_ASSETS_DIR};app/gui/assets",
        f"--add-data={ui_dir};ui",
        f"--add-data={ROOT_DIR / 'sitecustomize.py'};.",
        f"--add-data={ROOT_DIR / 'config.py'};.",
    ]

    # Include viral prompts & version file if they exist
    if (data_dir / "viral_prompts").exists():
        add_data_args.append(f"--add-data={data_dir / 'viral_prompts'};data/viral_prompts")
    if (data_dir / "app_version.txt").exists():
        add_data_args.append(f"--add-data={data_dir / 'app_version.txt'};data")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=WaqasAutomationPro",
    ] + add_data_args + [
        "--collect-all=app",
        "--collect-all=playwright",
        "--collect-all=supabase",
        "--collect-all=postgrest",
        "--collect-all=gotrue",
        "--collect-all=realtime",
        "--collect-all=storage3",
        "--collect-all=webview",
        "--collect-all=clr_loader",
        "--collect-all=pythonnet",
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
        "--hidden-import=webview",
        "--hidden-import=webview.platforms.winforms",
        "--hidden-import=webview.platforms.edgechromium",
        "--hidden-import=clr_loader",
        "--hidden-import=pythonnet",
        str(ROOT_DIR / "main.py")
    ] + icon_arg

    subprocess.check_call(cmd, cwd=str(ROOT_DIR))

    # Post-build safeguard: ensure UI & data directories exist in both root and _internal
    out_app_dir = DIST_DIR / "WaqasAutomationPro"
    internal_dir = out_app_dir / "_internal"

    if ui_dir.exists():
        for target in [out_app_dir / "ui", internal_dir / "ui"]:
            if not target.exists():
                shutil.copytree(ui_dir, target, dirs_exist_ok=True)
                print(f"[INFO] Copied UI assets to {target}")

    if (data_dir / "viral_prompts").exists():
        for target in [out_app_dir / "data" / "viral_prompts", internal_dir / "data" / "viral_prompts"]:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(data_dir / "viral_prompts", target, dirs_exist_ok=True)

    if (data_dir / "app_version.txt").exists():
        for target in [out_app_dir / "data" / "app_version.txt", internal_dir / "data" / "app_version.txt"]:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(data_dir / "app_version.txt", target)

    print("[3/3] PyInstaller build completed successfully!")

if __name__ == "__main__":
    build_executable()
