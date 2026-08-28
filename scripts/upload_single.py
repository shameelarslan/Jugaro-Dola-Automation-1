"""
Upload single-file 103MB installer to 1-Click Cloud Hosting (GoFile / FileTransfer).
"""

import sys
import time
import requests
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

INSTALLER_PATH = Path(r"c:\Users\I_T Computer\Antigravity\installer_output\WaqasAutomationPro_v2.0_Setup.exe")

def upload_single_file():
    file_size_mb = INSTALLER_PATH.stat().st_size / (1024 * 1024)
    print(f"[INFO] Target: Single File {INSTALLER_PATH.name} ({file_size_mb:.2f} MB)", flush=True)

    # 1. Try GoFile with proper headers
    print("[1/2] Connecting to GoFile high-speed CDN...", flush=True)
    try:
        srv_res = requests.get("https://api.gofile.io/servers", headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        if srv_res.status_code == 200:
            servers = srv_res.json().get("data", {}).get("servers", [])
            if servers:
                srv = servers[0].get("name")
                print(f"[INFO] Uploading to GoFile server ({srv})...", flush=True)
                up_url = f"https://{srv}.gofile.io/contents/uploadfile"
                with open(INSTALLER_PATH, "rb") as f:
                    r = requests.post(up_url, files={"file": (INSTALLER_PATH.name, f, "application/octet-stream")}, headers={"User-Agent": "Mozilla/5.0"}, timeout=600)
                if r.status_code == 200:
                    d = r.json().get("data", {})
                    dl_page = d.get("downloadPage")
                    if dl_page:
                        print("\n" + "=" * 70, flush=True)
                        print("🎉 1-CLICK SINGLE FILE DOWNLOAD LINK:", flush=True)
                        print(dl_page, flush=True)
                        print("=" * 70 + "\n", flush=True)
                        return dl_page
    except Exception as e:
        print(f"[WARNING] GoFile attempt note: {e}", flush=True)

    return None

if __name__ == "__main__":
    upload_single_file()
