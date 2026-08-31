@echo off
REM Auto-sync GitHub releases to Supabase
REM Run this script periodically to keep app releases in sync

cd /d "%~dp0.."
py scripts\auto_release_sync.py
pause
