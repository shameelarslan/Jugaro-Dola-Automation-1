@echo off
title Build Standalone Executable (.exe) — Tauri v2 Builder
color 0a
echo ================================================================
echo   BUILDING STANDALONE DESKTOP EXECUTABLE (.EXE) WITH TAURI V2
echo ================================================================
echo.
set "CARGO_TARGET_DIR=%LOCALAPPDATA%\tauri_build_cache"
cd /d "%~dp0src-tauri"
npx @tauri-apps/cli build
if errorlevel 1 (
    echo.
    echo [ERROR] Tauri build failed.
    pause
    exit /b %ERRORLEVEL%
)
echo.
echo ================================================================
echo   🎉 SUCCESS! Standalone Desktop Executable (.exe) built!
echo   Check folder: src-tauri\target\release\bundle\
echo ================================================================
echo.
pause
