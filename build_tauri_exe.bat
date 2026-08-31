@echo off
title Build Windows Installer - Waqas Automation Pro (Tauri v2 + Python sidecar)
color 0a
setlocal

echo ================================================================
echo   BUILDING WINDOWS INSTALLER (Tauri shell + frozen Python backend)
echo ================================================================
echo.

cd /d "%~dp0"

echo [1/4] Downloading Chromium into the bundle...
set "PLAYWRIGHT_BROWSERS_PATH=%~dp0src-tauri\resources\ms-playwright"
python -m playwright install chromium
if errorlevel 1 goto :failed

echo.
echo [2/4] Freezing the Python backend into a sidecar exe...
python scripts\build_server_sidecar.py
if errorlevel 1 goto :failed

echo.
echo [3/4] Building the Tauri bundles...
REM Reuse a shared Cargo cache outside the repo to keep rebuilds fast.
set "CARGO_TARGET_DIR=%LOCALAPPDATA%\tauri_build_cache"
cd /d "%~dp0src-tauri"
npx @tauri-apps/cli@^2 build
if errorlevel 1 goto :failed

echo.
echo [4/4] Done.
echo   Installer: %CARGO_TARGET_DIR%\release\bundle\nsis\
echo   MSI:       %CARGO_TARGET_DIR%\release\bundle\msi\
echo.
echo Chromium and the Python backend are bundled, so the installer runs
echo on a clean PC with no Python and no Playwright setup.
echo ================================================================
pause
exit /b 0

:failed
echo.
echo [ERROR] Build failed at the step above.
pause
exit /b 1
