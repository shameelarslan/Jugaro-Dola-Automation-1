@echo off
title Build Waqas Automation Pro Installer (.exe)
color 0b
cd /d "%~dp0"

echo ================================================================
echo        WAQAS AUTOMATION PRO - PRODUCTION INSTALLER BUILDER
echo ================================================================
echo.

set "PY_EXE="
if exist "C:\Users\msham\AppData\Local\Programs\Python\Python314\python.exe" (
    set "PY_EXE=C:\Users\msham\AppData\Local\Programs\Python\Python314\python.exe"
) else (
    where py >nul 2>nul && set "PY_EXE=py -3" || set "PY_EXE=python"
)

echo [1/3] Verifying build dependencies (PyInstaller, packaging, pillow)...
%PY_EXE% -m pip install pyinstaller packaging pillow --quiet

echo.
echo [2/3] Compiling Python code into Standalone Executable...
%PY_EXE% scripts\build_standalone.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] PyInstaller standalone compilation failed!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [3/3] Compiling Windows Installer Setup (.exe) via Inno Setup...
%PY_EXE% scripts\compile_installer.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Inno Setup compilation failed!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [SUCCESS] Windows Installer created successfully!
pause
