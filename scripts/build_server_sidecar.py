"""
Freezes the Python backend (app/server.py) into a self-contained Windows
sidecar that the Tauri shell launches — no Python installation required on
the end user's machine.

Output:
    dist/sidecar/WaqasAutomationServer/WaqasAutomationServer.exe   (+ _internal/)
    src-tauri/resources/server/                                    (copy Tauri bundles)

Usage:
    python scripts/build_server_sidecar.py
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "dist" / "sidecar"
WORK_DIR = ROOT_DIR / "build" / "sidecar"
TAURI_RESOURCES = ROOT_DIR / "src-tauri" / "resources"
SERVER_RESOURCE_DIR = TAURI_RESOURCES / "server"

APP_NAME = "WaqasAutomationServer"
SEP = ";" if os.name == "nt" else ":"

# Bundled read-only assets. Destination paths are relative to the PyInstaller
# _internal folder, which is what app/core/config.py resolves BASE_DIR to.
DATA_FILES = [
    (ROOT_DIR / "ui", "ui"),
    (ROOT_DIR / "app" / "gui" / "assets", "app/gui/assets"),
    (ROOT_DIR / "data" / "viral_prompts", "data/viral_prompts"),
    (ROOT_DIR / "data" / "app_version.txt", "data"),
    (ROOT_DIR / "config.py", "."),
]

# Packages that resolve resources at runtime and therefore need full collection.
COLLECT_ALL = [
    "playwright",
    "supabase",
    "postgrest",
    "gotrue",
    "realtime",
    "storage3",
    "supafunc",
    # Ships the ffmpeg binary used by the watermark remover.
    "imageio_ffmpeg",
]

HIDDEN_IMPORTS = [
    "config",
    "sqlite3",
    "openpyxl",
    "packaging",
    "packaging.version",
    "app.core.updater",
    "app.managers.session_manager",
    "app.automation.worker",
]

# The sidecar is headless: no Qt, no tkinter, no dataframes.
EXCLUDES = [
    "PyQt6",
    "PyQt5",
    "PySide6",
    "PySide2",
    "customtkinter",
    "tkinter",
    "pandas",
    "matplotlib",
    "scipy",
    "webview",
    "clr_loader",
    "pythonnet",
    "IPython",
    "pytest",
    "notebook",
]


def clean() -> None:
    print("[1/4] Cleaning previous sidecar artifacts...")
    for path in (DIST_DIR, WORK_DIR, SERVER_RESOURCE_DIR):
        shutil.rmtree(path, ignore_errors=True)


def build() -> Path:
    print(f"[2/4] Freezing app/server.py into {APP_NAME}.exe ...")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        # Console build: Rust spawns it with CREATE_NO_WINDOW so nothing is
        # visible, while stdout stays valid for the logger.
        "--console",
        f"--name={APP_NAME}",
        f"--distpath={DIST_DIR}",
        f"--workpath={WORK_DIR}",
        f"--specpath={WORK_DIR}",
    ]

    for src, dest in DATA_FILES:
        if src.exists():
            cmd.append(f"--add-data={src}{SEP}{dest}")
        else:
            print(f"  [WARN] Skipping missing data path: {src}")

    for pkg in COLLECT_ALL:
        cmd.append(f"--collect-all={pkg}")
    for mod in HIDDEN_IMPORTS:
        cmd.append(f"--hidden-import={mod}")
    for mod in EXCLUDES:
        cmd.append(f"--exclude-module={mod}")

    icon = ROOT_DIR / "app" / "gui" / "assets" / "logo.ico"
    if icon.exists():
        cmd.append(f"--icon={icon}")

    cmd.append(str(ROOT_DIR / "app" / "server.py"))

    subprocess.check_call(cmd, cwd=str(ROOT_DIR))

    out_dir = DIST_DIR / APP_NAME
    exe_path = out_dir / f"{APP_NAME}.exe"
    if os.name == "nt" and not exe_path.exists():
        raise SystemExit(f"[ERROR] Expected sidecar executable was not produced: {exe_path}")
    return out_dir


def stage_for_tauri(out_dir: Path) -> None:
    print(f"[3/4] Staging sidecar into {SERVER_RESOURCE_DIR} ...")
    SERVER_RESOURCE_DIR.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(out_dir, SERVER_RESOURCE_DIR, dirs_exist_ok=True)
    # Keep the placeholder so the Tauri resource glob still matches on a clean
    # checkout that has not built the sidecar yet.
    (SERVER_RESOURCE_DIR / ".gitkeep").write_text(
        "Placeholder so the Tauri resource glob always matches.\n"
        "The real contents are produced by: python scripts/build_server_sidecar.py\n",
        encoding="utf-8",
    )


def report() -> None:
    total = 0
    files = 0
    for path in SERVER_RESOURCE_DIR.rglob("*"):
        if path.is_file():
            total += path.stat().st_size
            files += 1
    print("[4/4] Sidecar ready.")
    print(f"      Files: {files}")
    print(f"      Size:  {total / (1024 * 1024):.1f} MB (uncompressed)")


if __name__ == "__main__":
    clean()
    stage_for_tauri(build())
    report()
