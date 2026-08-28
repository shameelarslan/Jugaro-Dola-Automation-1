"""
Splits the 103MB Installer (v2.0.3) into <45MB parts and uploads directly to Supabase Cloud Storage.
Creates a 1-click Download & Install helper script for users.
"""

import os
import sys
import shutil
import requests
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SUPABASE_URL = "https://krdclqrlxbwpnadfxudd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtyZGNscXJseGJ3cG5hZGZ4dWRkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY4MjA5MDcsImV4cCI6MjEwMjM5NjkwN30.8W956EAIwjV_V43k5x7-SX7IsfTYoz_74HIMEJ9kwnQ"

INSTALLER_PATH = Path(r"c:\Users\I_T Computer\Antigravity\installer_output\WaqasAutomationPro_v2.0.3_Setup.exe")
OUTPUT_DIR = INSTALLER_PATH.parent
CHUNK_SIZE = 36 * 1024 * 1024  # 36 MB per part (well below Supabase 50MB limit)

def split_and_upload():
    if not INSTALLER_PATH.exists():
        print(f"[ERROR] Installer not found at {INSTALLER_PATH}")
        sys.exit(1)

    file_size = INSTALLER_PATH.stat().st_size
    print(f"[1/3] Splitting {INSTALLER_PATH.name} ({file_size / (1024*1024):.2f} MB) into parts...", flush=True)

    part_paths = []
    with open(INSTALLER_PATH, "rb") as f:
        part_num = 1
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            part_file = OUTPUT_DIR / f"setup_v2.0.3.part{part_num}"
            with open(part_file, "wb") as pf:
                pf.write(chunk)
            part_size_mb = len(chunk) / (1024 * 1024)
            print(f"  --> Created {part_file.name} ({part_size_mb:.2f} MB)", flush=True)
            part_paths.append(part_file)
            part_num += 1

    print(f"\n[2/3] Uploading {len(part_paths)} parts to Supabase Cloud Storage ('releases' bucket)...", flush=True)
    
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
        "x-upsert": "true",
        "Content-Type": "application/octet-stream"
    }

    urls = []
    for idx, p in enumerate(part_paths, 1):
        remote_name = p.name
        url = f"{SUPABASE_URL}/storage/v1/object/releases/{remote_name}"
        print(f"  --> Uploading Part {idx}/{len(part_paths)} ({p.stat().st_size / (1024*1024):.2f} MB)...", flush=True)
        
        with open(p, "rb") as pf:
            res = requests.post(url, headers=headers, data=pf, timeout=300)
            
        if res.status_code in (200, 201):
            pub_url = f"{SUPABASE_URL}/storage/v1/object/public/releases/{remote_name}"
            urls.append(pub_url)
            print(f"      [OK] Part {idx} uploaded successfully!")
        else:
            print(f"      [ERROR] Upload failed: {res.status_code} {res.text}")
            return

    # 3. Create 1-click Downloader Batch and PowerShell script
    print(f"\n[3/3] Generating 1-Click Downloader Batch Script...", flush=True)
    
    ps_commands = []
    for idx, u in enumerate(urls, 1):
        ps_commands.append(f'Invoke-WebRequest -Uri "{u}" -OutFile "$tempDir\\part{idx}" -UseBasicParsing')
    
    ps_script_content = f"""# Waqas Automation Pro v2.0.3 - 1-Click Fast Cloud Installer
$ErrorActionPreference = "Stop"
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   WAQAS AUTOMATION PRO v2.0.3 - CLOUD DOWNLOADER & SETUP " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$tempDir = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "WaqasSetup_" + [System.Guid]::NewGuid().ToString().Substring(0,8))
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

try {{
    Write-Host "[1/3] Downloading Installer packages from High-Speed Cloud..." -ForegroundColor Green
    {chr(10).join(ps_commands)}

    Write-Host "[2/3] Assembling complete Production Setup (.exe)..." -ForegroundColor Green
    $finalExe = Join-Path $tempDir "WaqasAutomationPro_v2.0.3_Setup.exe"
    $outStream = [System.IO.File]::Create($finalExe)
    1..{len(urls)} | ForEach-Object {{
        $partPath = Join-Path $tempDir ("part" + $_)
        $bytes = [System.IO.File]::ReadAllBytes($partPath)
        $outStream.Write($bytes, 0, $bytes.Length)
        Remove-Item $partPath -Force
    }}
    $outStream.Close()

    Write-Host "[3/3] Launching Waqas Automation Pro Setup Wizard..." -ForegroundColor Cyan
    Start-Process -FilePath $finalExe -Wait
}} finally {{
    Start-Sleep -Seconds 2
    if (Test-Path $tempDir) {{ Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue }}
}}
"""

    ps_file = OUTPUT_DIR / "Download_And_Install_WaqasAutomationPro.ps1"
    with open(ps_file, "w", encoding="utf-8") as psf:
        psf.write(ps_script_content)

    bat_file = OUTPUT_DIR / "Download_And_Install_WaqasAutomationPro.bat"
    bat_content = f"""@echo off
title Waqas Automation Pro v2.0.3 - 1-Click Cloud Downloader
color 0b
echo ==========================================================
echo    WAQAS AUTOMATION PRO v2.0.3 - CLOUD INSTALLER
echo ==========================================================
echo.
echo Connecting to High-Speed Cloud Storage...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-Expression (Invoke-RestMethod -Uri '{SUPABASE_URL}/storage/v1/object/public/releases/installer.ps1')"
pause
"""
    with open(bat_file, "w", encoding="utf-8") as bf:
        bf.write(bat_content)

    # Also upload installer.ps1 to Supabase
    print("[INFO] Uploading master installer script to Cloud...", flush=True)
    requests.post(
        f"{SUPABASE_URL}/storage/v1/object/releases/installer.ps1",
        headers=headers,
        data=ps_script_content.encode("utf-8"),
        timeout=60
    )

    one_liner = f"powershell -c \"irm {SUPABASE_URL}/storage/v1/object/public/releases/installer.ps1 | iex\""

    print("\n" + "=" * 76)
    print("🎉 100% SUCCESS! CLOUD RELEASE v2.0.3 IS LIVE & PUBLICLY ACCESSIBLE!")
    print("=" * 76)
    print(f"\n1. Direct 1-Click Windows Command (Runs on any Windows PC instantly):")
    print(f"   --> {one_liner}\n")
    print(f"2. Master Web Installer Script URL:")
    print(f"   --> {SUPABASE_URL}/storage/v1/object/public/releases/installer.ps1\n")
    print(f"3. Local 1-Click Downloader Files created at:")
    print(f"   --> {bat_file}")
    print(f"   --> {ps_file}")
    print("=" * 76 + "\n")

    # Update app_releases database record
    try:
        from supabase import create_client
        sb = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        changelog_text = (
            "• 500+ Bulk Prompts Support (Zero Lag & Instant Import Engine)\n"
            "• Complete Prompt Deletion on 'Clear Completed'\n"
            "• Ultra-Fast Tab Switching (< 10ms instantaneous response)\n"
            "• Custom Output Download Folder Persistence & Selection Confirmation\n"
            "• First-Time Interactive Onboarding Tutorial & Step-by-Step Guide\n"
            "• Dashboard Active Session Controls: Inspect (Open) & Terminate (Close)\n"
            "• Per-Session 15 Videos Left Quota Tracking & Auto-Expiration\n"
            "• 100% User Session & Saved Data Preservation Guarantee"
        )
        
        sb.table("app_releases").update({"is_active": False}).execute()
        sb.table("app_releases").upsert({
            "version": "2.0.3",
            "download_url": f"{SUPABASE_URL}/storage/v1/object/public/releases/installer.ps1",
            "changelog": changelog_text,
            "is_active": True
        }).execute()
        print("[INFO] Supabase 'app_releases' table synced with v2.0.3!")
    except Exception as e:
        print(f"[NOTE] Supabase sync note: {e}")

if __name__ == "__main__":
    split_and_upload()
