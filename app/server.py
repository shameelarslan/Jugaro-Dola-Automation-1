"""
Python Sidecar API & Web Server for Waqas Automation Pro (Tauri / Web Frontend).
Exposes REST JSON endpoints and serves static UI files.
"""

import os
import sys
import json
import time
import base64
import urllib.parse
import threading
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# Add BASE_DIR to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.config import AppConfig, DEFAULT_DOWNLOAD_DIR
from app.core.database import db
from app.core.logger import logger

from app.core.cloud_manager import cloud_manager
from app.core.queue_manager import QueueManager
from app.managers.prompt_manager import PromptManager
from app.managers.viral_prompt_manager import viral_prompt_manager

# Global Queue Manager instance
global_config = db.load_app_config()
queue_manager = QueueManager(global_config)

def find_ui_dir() -> Path:
    candidates = []
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.extend([
            exe_dir / "_internal" / "ui",
            exe_dir / "ui",
            Path(getattr(sys, '_MEIPASS', '')) / "ui",
        ])
    candidates.extend([
        BASE_DIR / "ui",
        Path.cwd() / "ui",
        Path(__file__).resolve().parent.parent / "ui"
    ])
    for c in candidates:
        if c.exists() and (c / "index.html").exists():
            return c
    return BASE_DIR / "ui"

UI_DIR = find_ui_dir()

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    daemon_threads = True

class SidecarAPIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress standard HTTP access logging clutter
        pass

    def _send_json(self, data, status=200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, message, status=400):
        self._send_json({"success": False, "error": str(message)}, status=status)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # ── REST API ENDPOINTS ───────────────────────────────────────────────
        if path == "/api/stats":
            self._handle_get_stats()
        elif path == "/api/sessions":
            self._handle_get_sessions()
        elif path == "/api/prompts":
            self._handle_get_prompts()
        elif path == "/api/viral-prompts":
            q_search = query.get("q", [""])[0]
            self._handle_get_viral_prompts(q_search)
        elif path == "/api/automation/status":
            self._handle_get_automation_status()
        elif path == "/api/downloads":
            self._handle_get_downloads()
        elif path == "/api/super-admin/data":
            self._handle_get_super_admin_data()
        elif path == "/api/logs":
            self._handle_get_logs()
        elif path == "/api/config":
            cfg = db.load_app_config()
            self._send_json({"success": True, "config": cfg.to_dict()})
        elif path == "/api/check-update":
            self._handle_check_update()
        elif path == "/api/video/stream":
            video_path = query.get("path", [""])[0]
            self._handle_video_stream(video_path)
        else:
            # Serve Static UI Files
            self._serve_static(path)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            req_data = json.loads(body) if body else {}
        except Exception:
            req_data = {}

        if path == "/api/sessions/add":
            self._handle_add_session(req_data)
        elif path == "/api/sessions/bulk-import":
            self._handle_bulk_import_sessions(req_data)
        elif path == "/api/sessions/delete":
            self._handle_delete_session(req_data)
        elif path == "/api/sessions/bulk-delete":
            self._handle_bulk_delete_sessions(req_data)
        elif path == "/api/sessions/open-browser":
            self._handle_open_session_browser(req_data)
        elif path == "/api/sessions/toggle-status":
            self._handle_toggle_session_status(req_data)
        elif path == "/api/prompts/add":
            self._handle_add_prompt(req_data)
        elif path == "/api/prompts/bulk-add":
            self._handle_bulk_add_prompts(req_data)
        elif path == "/api/prompts/import-file":
            self._handle_import_prompts_file(req_data)
        elif path == "/api/prompts/delete":
            self._handle_delete_prompt(req_data)
        elif path == "/api/prompts/clear-all":
            self._handle_clear_all_prompts()
        elif path == "/api/prompts/clear-completed":
            self._handle_clear_completed_prompts()
        elif path == "/api/viral-prompts/add-to-queue":
            self._handle_add_viral_to_queue(req_data)
        elif path == "/api/automation/start":
            self._handle_start_automation(req_data)
        elif path == "/api/automation/stop":
            self._handle_stop_automation()
        elif path == "/api/downloads/open":
            self._handle_open_downloads_folder()
        elif path == "/api/super-admin/toggle-status":
            self._handle_toggle_user_status(req_data)
        elif path == "/api/super-admin/update-role":
            self._handle_update_user_role(req_data)
        elif path == "/api/config/update":
            self._handle_update_config(req_data)
        elif path == "/api/auth/login":
            self._handle_auth_login(req_data)
        elif path == "/api/auth/signup":
            self._handle_auth_signup(req_data)
        elif path == "/api/auth/logout":
            self._handle_auth_logout()
        elif path == "/api/system/apply-update":
            self._handle_apply_update(req_data)
        else:
            self._send_error("Endpoint not found", status=404)

    # ── HANDLERS IMPLEMENTATION ──────────────────────────────────────────────

    def _handle_get_stats(self):
        try:
            config = db.load_app_config()
            all_sessions = db.get_all_sessions()
            all_prompts = db.get_all_prompts()
            all_jobs = db.get_all_jobs()
            
            pending_p = len([p for p in all_prompts if p.get("status") == "Pending"])
            completed_p = len([p for p in all_prompts if p.get("status") == "Completed"])
            failed_p = len([p for p in all_prompts if p.get("status") == "Failed"])
            
            avail_sessions = len([s for s in all_sessions if s.get("status") == "Available"])
            expired_sessions = len([s for s in all_sessions if s.get("status") == "Expired"])
            running_sessions = len([s for s in all_sessions if s.get("status") in ("Running", "Busy", "Generating")])
            disabled_sessions = len([s for s in all_sessions if s.get("status") == "Disabled"])
            
            # Personalized stats for currently logged-in user
            user_stats = cloud_manager.fetch_user_dashboard_stats()
            user_total_videos = user_stats.get("total_videos", 0)
            user_today_videos = user_stats.get("today_videos", 0)
            user_daily_activity = user_stats.get("daily_activity", {})
            user_recent_videos = user_stats.get("recent_activity", [])

            # Cloud Super Stats (multi-tenant aggregated)
            cloud_user = cloud_manager.current_user or {}
            super_stats = cloud_manager.fetch_super_dashboard_stats()

            self._send_json({
                "success": True,
                "stats": {
                    "total_prompts": len(all_prompts),
                    "pending_prompts": pending_p,
                    "completed_prompts": completed_p,
                    "failed_prompts": failed_p,
                    "total_sessions": len(all_sessions),
                    "available_sessions": avail_sessions,
                    "expired_sessions": expired_sessions,
                    "running_sessions": running_sessions,
                    "disabled_sessions": disabled_sessions,
                    "lifetime_videos": user_total_videos,
                    "user_total_videos": user_total_videos,
                    "user_today_videos": user_today_videos,
                    "user_daily_activity": user_daily_activity,
                    "user_recent_videos": user_recent_videos,
                    "current_user": cloud_user,
                    "cloud_total_users": super_stats.get("total_users", 0),
                    "cloud_total_videos": super_stats.get("total_videos_all_time", 0),
                    "cloud_today_videos": super_stats.get("today_videos", 0),
                    "app_version": (lambda: (__import__("app.core.updater", fromlist=["get_installed_version"]).get_installed_version() if hasattr(sys, "modules") else "2.0.7"))(),
                    "config": config.to_dict()
                }
            })
        except Exception as e:
            self._send_error(e)

    def _handle_get_sessions(self):
        try:
            sessions = db.get_all_sessions()
            self._send_json({"success": True, "sessions": sessions})
        except Exception as e:
            self._send_error(e)

    def _handle_add_session(self, data):
        try:
            name = data.get("name", "").strip()
            session_type = data.get("session_type", "cookies_json" if data.get("cookie_data") else "Dola AI Pro")
            cookie_data = data.get("cookie_data", "")
            if not name:
                return self._send_error("Session name is required")
            
            sid = db.add_session(name=name, session_type=session_type, cookie_data=cookie_data)
            self._send_json({"success": True, "session_id": sid, "message": "Session created successfully!"})
        except Exception as e:
            self._send_error(e)

    def _handle_bulk_import_sessions(self, data):
        try:
            items = data.get("sessions", [])
            if not items:
                return self._send_error("No session items provided")
            
            added_count = 0
            for item in items:
                name = item.get("name", "").strip()
                cookie_data = item.get("cookie_data", "").strip()
                if name:
                    db.add_session(name=name, session_type="cookies_json" if cookie_data else "Dola AI Pro", cookie_data=cookie_data)
                    added_count += 1
            
            self._send_json({"success": True, "count": added_count, "message": f"Successfully imported {added_count} sessions!"})
        except Exception as e:
            self._send_error(e)

    def _handle_delete_session(self, data):
        try:
            sid = data.get("id")
            if sid is None:
                return self._send_error("Session ID is required")
            db.delete_session(sid)
            self._send_json({"success": True, "message": "Session deleted!"})
        except Exception as e:
            self._send_error(e)

    def _handle_open_session_browser(self, data):
        try:
            sid = data.get("id")
            if sid is None:
                return self._send_error("Session ID is required")
            from app.managers.session_manager import SessionManager
            SessionManager.launch_manual_browser_async(int(sid))
            self._send_json({"success": True, "message": f"Browser opened for session {sid}!"})
        except Exception as e:
            self._send_error(e)

    def _handle_toggle_session_status(self, data):
        try:
            sid = data.get("id")
            status = data.get("status", "Available")
            if sid is None:
                return self._send_error("Session ID is required")
            from app.managers.session_manager import SessionManager
            if status == "Available":
                SessionManager.make_session_available(int(sid))
            else:
                SessionManager.make_session_expired(int(sid))
            self._send_json({"success": True, "message": f"Session marked as {status}!"})
        except Exception as e:
            self._send_error(e)

    def _handle_bulk_delete_sessions(self, data):
        try:
            ids = data.get("ids", [])
            if not ids:
                return self._send_error("No session IDs provided")
            from app.managers.session_manager import SessionManager
            deleted = 0
            for sid in ids:
                try:
                    SessionManager.delete_session(int(sid))
                    deleted += 1
                except Exception:
                    pass
            self._send_json({"success": True, "count": deleted, "message": f"Deleted {deleted} session(s)!"})
        except Exception as e:
            self._send_error(e)

    def _handle_get_prompts(self):
        try:
            prompts = db.get_all_prompts()
            self._send_json({"success": True, "prompts": prompts})
        except Exception as e:
            self._send_error(e)

    def _handle_add_prompt(self, data):
        try:
            prompt_text = data.get("text", "").strip()
            category = data.get("category", "General")
            if not prompt_text:
                return self._send_error("Prompt text is required")

            pid = db.add_prompt(prompt_text=prompt_text, category=category)
            self._send_json({"success": True, "prompt_id": pid, "message": "Prompt added to queue!"})
        except Exception as e:
            self._send_error(e)

    def _handle_bulk_add_prompts(self, data):
        try:
            raw_prompts = data.get("prompts", [])
            category = (data.get("category") or "General").strip() or "General"
            if isinstance(raw_prompts, str):
                prompts_list = PromptManager.parse_text_lines(raw_prompts)
            elif isinstance(raw_prompts, list):
                prompts_list = [str(p).strip() for p in raw_prompts if str(p).strip()]
            else:
                prompts_list = []

            if not prompts_list:
                return self._send_error("No valid prompts provided in batch")

            added_count, duplicate_count = PromptManager.save_prompts(prompts_list, category=category)
            self._send_json({
                "success": True,
                "added_count": added_count,
                "duplicates_skipped": duplicate_count,
                "message": f"Successfully added {added_count} prompt(s) to queue! ({duplicate_count} duplicates skipped)"
            })
        except Exception as e:
            self._send_error(e)

    def _handle_import_prompts_file(self, data):
        try:
            file_name = data.get("file_name", "prompts.txt")
            file_data_b64 = data.get("file_data", "")
            category = (data.get("category") or "General").strip() or "General"

            if not file_data_b64:
                return self._send_error("No file data received")

            file_bytes = base64.b64decode(file_data_b64)
            prompts_list = PromptManager.import_from_bytes(file_bytes, file_name)

            if not prompts_list:
                return self._send_error(f"No valid prompts found in {file_name}")

            added_count, duplicate_count = PromptManager.save_prompts(prompts_list, category=category)
            self._send_json({
                "success": True,
                "added_count": added_count,
                "duplicates_skipped": duplicate_count,
                "file_name": file_name,
                "message": f"Successfully imported {added_count} prompt(s) from {file_name}! ({duplicate_count} duplicates skipped)"
            })
        except Exception as e:
            self._send_error(e)

    def _handle_delete_prompt(self, data):
        try:
            pid = data.get("id")
            if pid is None:
                return self._send_error("Prompt ID is required")
            db.delete_prompt(pid)
            self._send_json({"success": True, "message": "Prompt deleted!"})
        except Exception as e:
            self._send_error(e)

    def _handle_clear_all_prompts(self):
        try:
            db.clear_all_prompts()
            self._send_json({"success": True, "message": "All prompts cleared from queue successfully!"})
        except Exception as e:
            self._send_error(e)

    def _handle_clear_completed_prompts(self):
        try:
            count = db.clear_completed_prompts_and_jobs()
            self._send_json({"success": True, "count": count, "message": f"Cleared {count} completed prompt(s)!"})
        except Exception as e:
            self._send_error(e)

    def _handle_get_viral_prompts(self, search_query=""):
        try:
            vp_list = viral_prompt_manager.load_all_prompts()
            if search_query:
                sq = search_query.lower()
                vp_list = [p for p in vp_list if sq in p.get("title", "").lower() or sq in p.get("content", "").lower() or sq in p.get("category", "").lower()]
            self._send_json({"success": True, "count": len(vp_list), "prompts": vp_list})
        except Exception as e:
            self._send_error(e)


    def _handle_add_viral_to_queue(self, data):
        try:
            prompts = data.get("prompts", [])
            if not prompts:
                return self._send_error("No prompts selected")
            
            added_count = 0
            for p in prompts:
                text = p.get("prompt", "").strip()
                cat = p.get("category", "Viral Library")
                if text:
                    db.add_prompt(prompt_text=text, category=cat)
                    added_count += 1
                    
            self._send_json({"success": True, "added_count": added_count, "message": f"{added_count} viral prompts added to queue!"})
        except Exception as e:
            self._send_error(e)

    def _handle_get_automation_status(self):
        try:
            status_data = queue_manager.get_detailed_status() if hasattr(queue_manager, "get_detailed_status") else {
                "is_running": queue_manager._is_running,
                "is_paused": queue_manager._is_paused,
                "active_workers": len(queue_manager.workers),
                "concurrency_limit": queue_manager.concurrency_limit
            }
            self._send_json({"success": True, "automation": status_data})
        except Exception as e:
            self._send_error(e)

    def _handle_start_automation(self, data):
        try:
            if queue_manager._is_running:
                return self._send_error("Automation is already running!")

            all_prompts = db.get_pending_prompts()
            all_sessions = [s for s in db.get_all_sessions() if s.get("status") in ("Available", "Active")]

            if not all_prompts:
                return self._send_error("No pending prompts found in queue! Please add prompts first.")
            if not all_sessions:
                return self._send_error("No available sessions found! Please add at least 1 session.")

            run_id = queue_manager.prepare_and_start_automation(all_prompts, all_sessions)
            self._send_json({"success": True, "run_id": run_id, "message": f"Automation started! (Run ID: {run_id})"})
        except Exception as e:
            self._send_error(e)

    def _handle_stop_automation(self):
        try:
            queue_manager.stop_automation()
            self._send_json({"success": True, "message": "Stop requested. Workers are shutting down..."})
        except Exception as e:
            self._send_error(e)

    def _handle_get_downloads(self):
        try:
            cfg = db.load_app_config()
            out_dir = Path(cfg.default_download_dir)
            try:
                out_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                out_dir = Path(DEFAULT_DOWNLOAD_DIR)
                out_dir.mkdir(parents=True, exist_ok=True)

            files_info = []
            files = sorted(out_dir.glob("*.mp4"), key=lambda f: f.stat().st_mtime, reverse=True)
            
            for f in files:
                try:
                    st = f.stat()
                    size_mb = round(st.st_size / (1024 * 1024), 2)
                    mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))
                    files_info.append({
                        "name": f.name,
                        "path": str(f.resolve()),
                        "size_mb": size_mb,
                        "mtime": mtime
                    })
                except Exception:
                    pass

            self._send_json({
                "success": True,
                "download_dir": str(out_dir.resolve()),
                "total_files": len(files_info),
                "files": files_info
            })
        except Exception as e:
            self._send_error(e)

    def _handle_open_downloads_folder(self):
        try:
            cfg = db.load_app_config()
            out_dir = Path(cfg.default_download_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            
            if os.name == 'nt':
                os.startfile(str(out_dir.resolve()))
            else:
                subprocess.Popen(["xdg-open", str(out_dir.resolve())])

            self._send_json({"success": True, "message": "Opened downloads directory!"})
        except Exception as e:
            self._send_error(e)

    def _handle_video_stream(self, video_path_str: str):
        try:
            if not video_path_str:
                self.send_error(400, "Missing video path parameter")
                return

            v_path = Path(video_path_str)
            if not v_path.exists() or not v_path.is_file():
                # Try finding in default download directory by basename
                cfg = db.load_app_config()
                alt_path = Path(cfg.default_download_dir) / v_path.name
                if alt_path.exists() and alt_path.is_file():
                    v_path = alt_path
                else:
                    self.send_error(404, "Video file not found")
                    return

            file_size = v_path.stat().st_size
            range_header = self.headers.get("Range")

            if range_header:
                # Handle Byte-Range requests for seeking in HTML5 Video Player
                try:
                    bytes_part = range_header.replace("bytes=", "").strip()
                    parts = bytes_part.split("-")
                    start = int(parts[0]) if parts[0] else 0
                    end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
                    if end >= file_size:
                        end = file_size - 1
                    chunk_length = (end - start) + 1

                    self.send_response(206)
                    self.send_header("Content-Type", "video/mp4")
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                    self.send_header("Content-Length", str(chunk_length))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()

                    with open(v_path, "rb") as f:
                        f.seek(start)
                        bytes_to_send = chunk_length
                        while bytes_to_send > 0:
                            chunk = f.read(min(bytes_to_send, 64 * 1024))
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            bytes_to_send -= len(chunk)
                    return
                except Exception as stream_err:
                    # Client probably closed playback connection, ignore
                    return
            else:
                self.send_response(200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Content-Length", str(file_size))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                with open(v_path, "rb") as f:
                    while True:
                        chunk = f.read(64 * 1024)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
        except Exception as e:
            try:
                self.send_error(500, f"Error streaming video: {e}")
            except Exception:
                pass

    def _handle_get_super_admin_data(self):
        try:
            import importlib
            import app.core.cloud_manager
            importlib.reload(app.core.cloud_manager)
            from app.core.cloud_manager import cloud_manager
            data = cloud_manager.fetch_super_dashboard_stats(True)
            self._send_json({"success": True, "super_admin": data})
        except Exception as e:
            self._send_error(e)

    def _handle_toggle_user_status(self, data):
        try:
            uid = data.get("user_id")
            new_status = data.get("new_status")
            if not uid or not new_status:
                return self._send_error("user_id and new_status required")

            success = cloud_manager.toggle_user_status(uid, new_status)
            if success:
                self._send_json({"success": True, "message": f"User status updated to {new_status}"})
            else:
                self._send_error("Failed to update status in Supabase")
        except Exception as e:
            self._send_error(e)

    def _handle_update_user_role(self, data):
        try:
            uid = data.get("user_id")
            new_role = data.get("new_role")
            if not uid or not new_role:
                return self._send_error("user_id and new_role required")

            success = cloud_manager.update_user_role(uid, new_role)
            if success:
                self._send_json({"success": True, "message": f"User role updated to {new_role}"})
            else:
                self._send_error("Failed to update user role")
        except Exception as e:
            self._send_error(e)

    def _handle_check_update(self):
        """Checks Supabase for available updates for the current user."""
        try:
            from app.core.cloud_manager import cloud_manager
            update_info = cloud_manager.check_for_update()
            if update_info:
                self._send_json({
                    "success": True,
                    "update_available": True,
                    "version": update_info["version"],
                    "current_version": update_info["current_version"],
                    "download_url": update_info["download_url"],
                    "release_notes": update_info["release_notes"],
                    "is_mandatory": update_info["is_mandatory"]
                })
            else:
                self._send_json({"success": True, "update_available": False})
        except Exception as e:
            self._send_json({"success": True, "update_available": False, "error": str(e)})

    def _handle_apply_update(self, data):
        """Downloads and applies the update patch package automatically."""
        try:
            download_url = (data.get("download_url") or "").strip()
            version_str = (data.get("version") or "").strip()
            if not download_url:
                return self._send_error("download_url is required")

            from app.core.updater import updater
            success = updater.download_and_install_update(download_url, version_str=version_str)
            if success:
                self._send_json({
                    "success": True,
                    "message": f"Update to v{version_str} installed successfully!"
                })
            else:
                self._send_error("Failed to download or apply the update package.")
        except Exception as e:
            self._send_error(f"Error applying update: {e}")

    def _handle_get_logs(self):
        try:
            entries = logger.get_recent_entries(limit=200)
            self._send_json({"success": True, "logs": entries})
        except Exception as e:
            self._send_error(e)

    def _handle_auth_login(self, data):
        try:
            email = (data.get("email") or "").strip()
            password = (data.get("password") or "").strip()
            if not email or not password:
                return self._send_error("Email and password are required")

            success, msg = cloud_manager.login(email, password)
            if success:
                self._send_json({"success": True, "message": msg, "user": cloud_manager.current_user})
            else:
                self._send_error(msg)
        except Exception as e:
            self._send_error(str(e))

    def _handle_auth_signup(self, data):
        try:
            email = (data.get("email") or "").strip()
            password = (data.get("password") or "").strip()
            full_name = (data.get("full_name") or "").strip()
            whatsapp = (data.get("whatsapp_number") or "").strip()
            if not email or not password:
                return self._send_error("Email and password are required")

            success, msg, status = cloud_manager.signup(email, password, full_name, whatsapp)
            if success:
                self._send_json({"success": True, "message": msg, "status": status, "user": cloud_manager.current_user})
            else:
                self._send_error(msg)
        except Exception as e:
            self._send_error(str(e))

    def _handle_auth_logout(self):
        try:
            cloud_manager.logout()
            self._send_json({"success": True, "message": "Logged out successfully"})
        except Exception as e:
            self._send_error(str(e))


    def _handle_update_config(self, data):
        try:
            cfg = db.load_app_config()
            for k, v in data.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)
            db.save_app_config(cfg)
            self._send_json({"success": True, "message": "Configuration updated!", "config": cfg.to_dict()})
        except Exception as e:
            self._send_error(e)

    def _serve_static(self, path):
        if path == "/" or not path:
            path = "/index.html"
            
        file_path = (UI_DIR / path.lstrip("/")).resolve()
        
        # Security check: ensure path is within UI_DIR
        if not str(file_path).startswith(str(UI_DIR.resolve())):
            self.send_error(403, "Forbidden")
            return

        if not file_path.exists() or file_path.is_dir():
            file_path = UI_DIR / "index.html"

        content_type = "text/html"
        if file_path.suffix == ".css":
            content_type = "text/css"
        elif file_path.suffix == ".js":
            content_type = "application/javascript"
        elif file_path.suffix == ".json":
            content_type = "application/json"
        elif file_path.suffix == ".png":
            content_type = "image/png"
        elif file_path.suffix in (".jpg", ".jpeg"):
            content_type = "image/jpeg"
        elif file_path.suffix == ".svg":
            content_type = "image/svg+xml"

        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8" if "text" in content_type else content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(404, f"File not found: {e}")

def run_server(port=8765):
    server_address = ("127.0.0.1", port)
    httpd = ThreadedHTTPServer(server_address, SidecarAPIHandler)
    logger.info(f"🌐 Sidecar REST API & Web Server running on http://127.0.0.1:{port}", category="SERVER")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Sidecar server shutting down cleanly...", category="SERVER")
        httpd.server_close()

if __name__ == "__main__":
    port = 8765
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)
