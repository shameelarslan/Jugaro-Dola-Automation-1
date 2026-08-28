@echo off
title Waqas Automation Pro
cd /d "C:\Users\I_T Computer\Antigravity"
"C:\Users\I_T Computer\AppData\Local\Programs\Python\Python314\python.exe" main.py
if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)
