"""
Upload installer to High-Speed Public Cloud with direct download link.
Supports Pixeldrain & GoFile APIs.
"""

import os
import sys
import requests
from pathlib import Path

INSTALLER_PATH = Path(r"c:\Users\I_T Computer\Antigravity\installer_output\WaqasAutomationPro_v2.0_Setup.exe")

def upload_pixeldrain():
    print(f"[INFO] Uploading {INSTALLER_PATH.name} to Pixeldrain (High-Speed Cloud)...", flush=True)
    url = f"https://pixeldrain.com/api/file/{INSTALLER_PATH.name}"
    
    with open(INSTALLER_PATH, "rb") as f:
        res = requests.put(url, data=f, timeout=600)
    
    if res.status_code in (200, 201):
        data = res.json()
        file_id = data.get("id")
        view_url = f"https://pixeldrain.com/u/{file_id}"
        direct_download_url = f"https://pixeldrain.com/api/file/{file_id}"
        return view_url, direct_download_url
    else:
        print(f"[ERROR] Pixeldrain upload failed: {res.status_code} {res.text}", flush=True)
        return None, None

def upload_gofile():
    print(f"[INFO] Uploading {INSTALLER_PATH.name} to GoFile...", flush=True)
    # 1. Get best server
    srv_res = requests.get("https://api.gofile.io/servers", timeout=30)
    if srv_res.status_code == 200:
        servers = srv_res.json().get("data", {}).get("servers", [])
        if servers:
            server = servers[0].get("name")
            upload_url = f"https://{server}.gofile.io/contents/uploadfile"
            with open(INSTALLER_PATH, "rb") as f:
                up_res = requests.post(upload_url, files={"file": f}, timeout=600)
            if up_res.status_code == 200:
                data = up_res.json().get("data", {})
                download_page = data.get("downloadPage")
                return download_page
    return None

if __name__ == "__main__":
    if not INSTALLER_PATH.exists():
        print(f"[ERROR] Installer not found at {INSTALLER_PATH}")
        sys.exit(1)
        
    p_view, p_direct = upload_pixeldrain()
    if p_view:
        print("\n" + "=" * 70)
        print("🎉 SUCCESS! FILE UPLOADED TO CLOUD")
        print(f"📥 Easy User Download Page: {p_view}")
        print(f"🔗 Direct 1-Click Download: {p_direct}")
        print("=" * 70 + "\n")
    else:
        print("[INFO] Trying GoFile fallback...")
        g_url = upload_gofile()
        if g_url:
            print(f"🎉 GoFile Download Link: {g_url}")
