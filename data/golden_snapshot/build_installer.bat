@echo off
title Build Waqas Automation Pro Installer (.exe)
color 0b

echo ================================================================
echo        WAQAS AUTOMATION PRO - PRODUCTION INSTALLER BUILDER
echo ================================================================
echo.

echo [1/3] Verifying build dependencies (PyInstaller, packaging, pillow)...
pip install pyinstaller packaging pillow --quiet

echo.
echo [2/3] Compiling Python code into Standalone Executable...
python scripts\build_standalone.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] PyInstaller standalone compilation failed!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [3/3] Compiling Windows Installer Setup (.exe) via Inno Setup...
python scripts\compile_installer.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Inno Setup compilation failed!
    pause
    exit /b %ERRORLEVEL%
)

echo.
pause
