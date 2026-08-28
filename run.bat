@echo off
title Waqas Automation Pro v2.0.7 - Commercial SaaS Desktop
cd /d "%~dp0"

if exist "C:\Users\msham\AppData\Local\Programs\Python\Python314\python.exe" (
    "C:\Users\msham\AppData\Local\Programs\Python\Python314\python.exe" main.py %*
) else (
    py -3 main.py %* 2>nul || python main.py %*
)

if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)
