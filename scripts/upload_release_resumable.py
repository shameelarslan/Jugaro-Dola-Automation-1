"""
Upload script for Supabase Storage with TUS Resumable Upload or Direct Streaming
"""

import os
import sys
import requests
from pathlib import Path

SUPABASE_URL = "https://krdclqrlxbwpnadfxudd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtyZGNscXJseGJ3cG5hZGZ4dWRkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY4MjA5MDcsImV4cCI6MjEwMjM5NjkwN30.8W956EAIwjV_V43k5x7-SX7IsfTYoz_74HIMEJ9kwnQ"

INSTALLER_PATH = Path(r"c:\Users\I_T Computer\Antigravity\installer_output\WaqasAutomationPro_v2.0_Setup.exe")

def upload():
    file_size = INSTALLER_PATH.stat().st_size
    file_size_mb = file_size / (1024 * 1024)
    file_name = "WaqasAutomationPro_v2.0_Setup.exe"
    
    print(f"[INFO] Uploading {file_name} ({file_size_mb:.2f} MB)...", flush=True)

    # Supabase standard storage object endpoint
    url = f"{SUPABASE_URL}/storage/v1/object/releases/{file_name}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
        "x-upsert": "true",
        "Content-Type": "application/x-msdownload"
    }

    # Custom file reader with progress
    class ProgressFileReader:
        def __init__(self, filepath, total_bytes):
            self.f = open(filepath, "rb")
            self.total = total_bytes
            self.uploaded = 0
            self.last_percent = 0

        def read(self, size=-1):
            chunk = self.f.read(size)
            if chunk:
                self.uploaded += len(chunk)
                pct = int((self.uploaded / self.total) * 100)
                if pct != self.last_percent and pct % 5 == 0:
                    self.last_percent = pct
                    mb_up = self.uploaded / (1024 * 1024)
                    print(f"  --> Progress: {pct}% ({mb_up:.1f}/{file_size_mb:.1f} MB)", flush=True)
            return chunk

        def __len__(self):
            return self.total

        def close(self):
            self.f.close()

    reader = ProgressFileReader(INSTALLER_PATH, file_size)
    try:
        response = requests.post(url, headers=headers, data=reader, timeout=600)
        reader.close()
        print(f"[INFO] Server response code: {response.status_code}", flush=True)
        print(f"[INFO] Server response body: {response.text}", flush=True)

        if response.status_code in (200, 201):
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/releases/{file_name}"
            print("\n" + "=" * 70, flush=True)
            print("🚀 PUBLIC DIRECT DOWNLOAD LINK:", flush=True)
            print(public_url, flush=True)
            print("=" * 70 + "\n", flush=True)
            return public_url
        else:
            print(f"[ERROR] Upload failed with status {response.status_code}", flush=True)
            return None
    except Exception as e:
        reader.close()
        print(f"[ERROR] Exception during upload: {e}", flush=True)
        return None

if __name__ == "__main__":
    upload()
