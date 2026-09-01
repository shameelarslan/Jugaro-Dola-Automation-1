"""
Upload installer to High-Speed Public Cloud with direct download link.
Uses Pixeldrain & GoFile via pure standard library (urllib).
"""

import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent.parent
INSTALLER_PATH = ROOT_DIR / "installer_output" / "WaqasAutomationPro_v2.1.3_Setup.exe"

def upload_pixeldrain():
    print(f"[INFO] Uploading {INSTALLER_PATH.name} ({INSTALLER_PATH.stat().st_size / (1024*1024):.1f} MB) to Pixeldrain...", flush=True)
    url = f"https://pixeldrain.com/api/file/{INSTALLER_PATH.name}"
    
    with open(INSTALLER_PATH, "rb") as f:
        data = f.read()
    
    req = urllib.request.Request(url, data=data, method="PUT")
    req.add_header("User-Agent", "WaqasAutomationProUploader/1.0")
    
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            res_body = resp.read().decode('utf-8')
            data = json.loads(res_body)
            file_id = data.get("id")
            view_url = f"https://pixeldrain.com/u/{file_id}"
            direct_download_url = f"https://pixeldrain.com/api/file/{file_id}"
            return view_url, direct_download_url
    except Exception as e:
        print(f"[ERROR] Pixeldrain upload failed: {e}", flush=True)
        return None, None

def upload_gofile():
    print(f"[INFO] Uploading {INSTALLER_PATH.name} to GoFile...", flush=True)
    try:
        req = urllib.request.Request("https://api.gofile.io/servers")
        with urllib.request.urlopen(req, timeout=30) as resp:
            srv_data = json.loads(resp.read().decode('utf-8'))
            servers = srv_data.get("data", {}).get("servers", [])
            if not servers:
                return None
            server = servers[0].get("name")
        
        # Simple multipart upload
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        with open(INSTALLER_PATH, "rb") as f:
            file_bytes = f.read()
        
        body = bytearray()
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="file"; filename="{INSTALLER_PATH.name}"\r\n'.encode())
        body.extend(b"Content-Type: application/octet-stream\r\n\r\n")
        body.extend(file_bytes)
        body.extend(f"\r\n--{boundary}--\r\n".encode())
        
        upload_url = f"https://{server}.gofile.io/contents/uploadfile"
        req = urllib.request.Request(upload_url, data=body, method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        req.add_header("User-Agent", "WaqasAutomationProUploader/1.0")
        
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = json.loads(resp.read().decode('utf-8')).get("data", {})
            return data.get("downloadPage")
    except Exception as e:
        print(f"[ERROR] GoFile upload failed: {e}", flush=True)
        return None

if __name__ == "__main__":
    if not INSTALLER_PATH.exists():
        print(f"[ERROR] Installer not found at {INSTALLER_PATH}")
        sys.exit(1)
        
    p_view, p_direct = upload_pixeldrain()
    if p_view:
        print("\n" + "=" * 70)
        print("🎉 SUCCESS! 118MB PRODUCTION INSTALLER UPLOADED TO CLOUD")
        print(f"📥 Direct Download Page: {p_view}")
        print(f"🔗 Direct 1-Click Link: {p_direct}")
        print("=" * 70 + "\n")
    else:
        print("[INFO] Trying GoFile fallback...")
        g_url = upload_gofile()
        if g_url:
            print(f"🎉 GoFile Download Link: {g_url}")
