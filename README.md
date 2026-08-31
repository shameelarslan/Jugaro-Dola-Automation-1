# FB AutoViral SaaS Pro

Modern Windows Desktop Application for Facebook Account & Reel Automation with verification-first state machine architecture.

## Milestone 1 Overview

Milestone 1 implements the application foundation:
- Modular folder structure & package layout
- CustomTkinter dark-mode desktop GUI shell with non-blocking threading
- Dedicated Playwright Desktop Chromium Browser Manager
- Configurable physical browser window (e.g. 400x400 debug mode, user resizable/draggable)
- Debug Mode toggle (headless=False visible window + slow_mo delay)
- Persistent browser session & profile storage foundation (`data/accounts/{account_id}/`)
- Thread-safe structured logging & live log streaming panel
- Error screenshot capture utility
- SQLite database layer using Python standard library `sqlite3`

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright Chromium browser binaries:
```bash
python -m playwright install chromium
```

## Running the Application

Launch the desktop GUI:
```bash
python main.py
```

## Running Independent Browser Launch Test

To test the Playwright Chromium browser launch independently:
```bash
python tests/test_browser.py
```

## Building the Windows installer

The shipped app is a Tauri shell that launches a frozen copy of the Python
backend, so the end user needs neither Python nor Playwright installed. Three
pieces go into the bundle: the Rust/Tauri shell, the PyInstaller sidecar built
from `app/server.py`, and a Chromium download placed under
`src-tauri/resources/ms-playwright`.

### On GitHub (recommended)

`.github/workflows/build-windows.yml` does the whole thing on a
`windows-latest` runner. Push a version tag and the workflow builds and
publishes a GitHub Release with the installer attached:

```bash
python scripts/sync_version.py 2.1.2   # stamp the version everywhere
git commit -am "Release v2.1.2"
git tag v2.1.2
git push origin main --tags
```

Running the workflow manually from the Actions tab (optional `version` input)
builds the same files and uploads them as a downloadable artifact instead of
creating a release.

Outputs: `WaqasAutomationPro_v<ver>_Setup.exe` (NSIS, per-user, no admin),
`WaqasAutomationPro_v<ver>_x64.msi` (machine-wide, needs admin) and
`WaqasAutomationPro_v<ver>_Portable.zip` (unzip and run).

### Locally

One-click: run `build_tauri_exe.bat` (downloads Chromium, freezes the backend,
builds the bundles). Or step by step:

```bash
pip install -r requirements.txt pyinstaller
set PLAYWRIGHT_BROWSERS_PATH=%CD%\src-tauri\resources\ms-playwright
python -m playwright install chromium
python scripts/build_server_sidecar.py
cd src-tauri && npx @tauri-apps/cli@^2 build
```

Bundles land in `src-tauri/target/release/bundle/{nsis,msi}` (the .bat uses a
shared Cargo cache under `%LOCALAPPDATA%\tauri_build_cache` instead).

Notes: the build is not code-signed, so SmartScreen shows "unknown publisher"
on first run; WebView2 is installed by a download bootstrapper, so the
installer needs internet on machines that do not already have it (Windows 11
and up-to-date Windows 10 do). Because Chromium and the frozen backend are
bundled, the installer is large — roughly 200-350 MB.
