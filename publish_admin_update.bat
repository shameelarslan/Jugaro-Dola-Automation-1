@echo off
title Publish Admin Auto-Update
color 0a
cd /d "%~dp0"

echo ================================================================
echo        WAQAS AUTOMATION PRO - PUBLISH ADMIN-ONLY UPDATE
echo ================================================================
echo.

set "PY_EXE="
if exist "C:\Users\msham\AppData\Local\Programs\Python\Python314\python.exe" (
    set "PY_EXE=C:\Users\msham\AppData\Local\Programs\Python\Python314\python.exe"
) else (
    where py >nul 2>nul && set "PY_EXE=py -3" || set "PY_EXE=python"
)

%PY_EXE% scripts\publish_admin_update.py %*

echo.
pause
