@echo off
title Launching Waqas Automation Pro — Tauri Native Desktop App
color 0b
echo ================================================================
echo   LAUNCHING TAURI V2 NATIVE DESKTOP WINDOW (NO BROWSER NEEDED)
echo ================================================================
echo.
set "CARGO_TARGET_DIR=%LOCALAPPDATA%\tauri_build_cache"
cd /d "%~dp0src-tauri"
npx @tauri-apps/cli dev
if errorlevel 1 (
    echo.
    echo [ERROR] Could not start Tauri dev process.
    pause
)
