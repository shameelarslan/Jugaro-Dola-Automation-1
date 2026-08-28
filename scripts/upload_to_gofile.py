"""
GoFile Uploader for 100MB+ Installers (ASCII Safe)
"""

import os
import sys
import json
import requests
from pathlib import Path

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

INSTALLER_PATH = Path(r"c:\Users\I_T Computer\Antigravity\installer_output\WaqasAutomationPro_v2.0_Setup.exe")
SUPABASE_URL = "https://krdclqrlxbwpnadfxudd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtyZGNscXJseGJ3cG5hZGZ4dWRkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY4MjA5MDcsImV4cCI6MjEwMjM5NjkwN30.8W956EAIwjV_V43k5x7-SX7IsfTYoz_74HIMEJ9kwnQ"

def upload_to_gofile():
    print("[1/3] Finding best GoFile server...", flush=True)
    srv_resp = requests.get("https://api.gofile.io/servers", timeout=30)
    if srv_resp.status_code != 200:
        print(f"[ERROR] Could not fetch GoFile servers: {srv_resp.text}")
        return None
        
    servers = srv_resp.json().get("data", {}).get("servers", [])
    if not servers:
        print("[ERROR] No servers returned by GoFile")
        return None
        
    server = servers[0].get("name")
    upload_url = f"https://{server}.gofile.io/contents/uploadfile"
    print(f"[2/3] Uploading installer to GoFile ({server})...", flush=True)

    with open(INSTALLER_PATH, "rb") as f:
        resp = requests.post(upload_url, files={"file": f}, timeout=600)

    if resp.status_code == 200:
        res_data = resp.json()
        if res_data.get("status") == "ok":
            data = res_data.get("data", {})
            download_page = data.get("downloadPage")
            file_id = data.get("fileId")
            fileName = data.get("fileName")
            
            print("\n" + "=" * 70, flush=True)
            print("[SUCCESS] Production Installer Uploaded Successfully!", flush=True)
            print(f"File Name: {fileName}", flush=True)
            print(f"Download Link: {download_page}", flush=True)
            print("=" * 70 + "\n", flush=True)
            
            # Save link to disk
            link_file = INSTALLER_PATH.parent / "LATEST_DOWNLOAD_LINK.txt"
            with open(link_file, "w", encoding="utf-8") as lf:
                lf.write(f"Waqas Automation Pro v2.0 Installer Download Link:\n{download_page}\n")
            print(f"[INFO] Saved link to {link_file}")

            # Register in Supabase Cloud releases table
            try:
                from supabase import create_client
                sb = create_client(SUPABASE_URL, SUPABASE_KEY)
                sb.table("app_releases").insert({
                    "version": "2.0.0",
                    "download_url": download_page,
                    "release_notes": "Production Release v2.0 - Multi-User SaaS & Cloud Security",
                    "is_active": True
                }).execute()
                print("[INFO] Release registered in Supabase Cloud database!")
            except Exception as e:
                print(f"[NOTE] Supabase sync note: {e}")

            return download_page
        else:
            print(f"[ERROR] GoFile API status: {res_data}")
    else:
        print(f"[ERROR] GoFile upload failed with HTTP {resp.status_code}: {resp.text}")
    return None

if __name__ == "__main__":
    upload_to_gofile()
