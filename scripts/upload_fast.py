"""
Multi-Cloud Fast Uploader for Waqas Automation Pro Installer
Uploads to tmpfiles.org and catbox litterbox for instant direct links.
"""

import sys
import requests
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

INSTALLER_PATH = Path(r"c:\Users\I_T Computer\Antigravity\installer_output\WaqasAutomationPro_v2.0_Setup.exe")

def upload_tmpfiles():
    print("[1/2] Uploading to tmpfiles.org CDN...", flush=True)
    url = "https://tmpfiles.org/api/v1/upload"
    with open(INSTALLER_PATH, "rb") as f:
        res = requests.post(url, files={"file": f}, timeout=180)
    
    if res.status_code == 200:
        data = res.json().get("data", {})
        full_url = data.get("url", "")
        if full_url:
            # Convert to direct download link: https://tmpfiles.org/123/file.exe -> https://tmpfiles.org/dl/123/file.exe
            direct_dl = full_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
            print("\n" + "=" * 70, flush=True)
            print("🚀 TMPFILES DIRECT DOWNLOAD LINK:", flush=True)
            print(direct_dl, flush=True)
            print("=" * 70 + "\n", flush=True)
            return direct_dl
    return None

def upload_litterbox():
    print("[2/2] Uploading to Catbox Litterbox Cloud...", flush=True)
    url = "https://litterbox.catbox.moe/resources/internals/api.php"
    with open(INSTALLER_PATH, "rb") as f:
        res = requests.post(url, data={"reqtype": "fileupload", "time": "72h"}, files={"fileToUpload": f}, timeout=180)
    
    if res.status_code == 200 and res.text.startswith("http"):
        link = res.text.strip()
        print("\n" + "=" * 70, flush=True)
        print("🚀 LITTERBOX DIRECT DOWNLOAD LINK:", flush=True)
        print(link, flush=True)
        print("=" * 70 + "\n", flush=True)
        return link
    return None

if __name__ == "__main__":
    link = upload_tmpfiles()
    if not link:
        upload_litterbox()
