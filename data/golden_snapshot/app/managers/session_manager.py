"""
Session Manager Module for Cookie JSON / Netscape / Chrome Profile Folder management.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from app.core.database import db
from app.core.logger import logger

class SessionManager:
    @staticmethod
    def parse_cookie_json(raw_json: str) -> List[Dict[str, Any]]:
        """Parse and sanitize a JSON string of browser cookies."""
        try:
            data = json.loads(raw_json)
            if isinstance(data, dict):
                data = [data]
            if not isinstance(data, list):
                raise ValueError("Cookies JSON must be a list of cookie objects.")
            
            cleaned = []
            for item in data:
                if isinstance(item, dict) and "name" in item and "value" in item:
                    cleaned.append({
                        "name": str(item["name"]),
                        "value": str(item["value"]),
                        "domain": str(item.get("domain", ".dola.com")),
                        "path": str(item.get("path", "/")),
                        "secure": bool(item.get("secure", True)),
                        "httpOnly": bool(item.get("httpOnly", False)),
                    })
            return cleaned
        except Exception as e:
            raise ValueError(f"Invalid Cookie JSON format: {e}")

    @staticmethod
    def add_session(name: str, session_type: str, cookie_data: Optional[str] = None, profile_path: Optional[str] = None) -> int:
        """
        Adds a new session into the database.
        session_type: 'cookies_json', 'cookies_netscape', or 'profile_dir'
        """
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Session name cannot be empty.")

        if session_type in ("cookies_json", "cookies_netscape"):
            if not cookie_data or not cookie_data.strip():
                raise ValueError("Cookie data cannot be empty for cookie session.")
            # Validate JSON if cookies_json
            if session_type == "cookies_json":
                SessionManager.parse_cookie_json(cookie_data)

        elif session_type == "profile_dir":
            if not profile_path or not Path(profile_path).exists():
                raise ValueError(f"Profile folder path does not exist: {profile_path}")

        else:
            raise ValueError(f"Unknown session type: {session_type}")

        session_id = db.add_session(clean_name, session_type, cookie_data, profile_path)
        logger.info(f"Added new session '{clean_name}' (ID: {session_id}, Type: {session_type}).", category="SESSIONS")
        return session_id

    @staticmethod
    def import_sessions_from_directory(profiles_dir: str) -> int:
        """Automatically scans a folder containing Chrome profile shortcuts or profile subfolders."""
        dir_path = Path(profiles_dir)
        if not dir_path.exists() or not dir_path.is_dir():
            raise FileNotFoundError(f"Profiles directory not found: {profiles_dir}")

        added_count = 0
        for item in sorted(dir_path.iterdir()):
            if item.is_dir():
                s_name = item.name
                try:
                    SessionManager.add_session(s_name, "profile_dir", profile_path=str(item))
                    added_count += 1
                except Exception:
                    pass

        logger.info(f"Imported {added_count} profile directories from {profiles_dir}.", category="SESSIONS")
        return added_count

    @staticmethod
    def delete_session(session_id: int) -> bool:
        """
        Deletes a session from DB if not BUSY. Does NOT delete profile files on disk.
        """
        sess = db.get_session(session_id)
        if not sess:
            return False
            
        if sess.get("status") in ("Busy", "Running", "Generating"):
            raise ValueError("This session is currently in use and cannot be deleted.")

        db.delete_session(session_id)
        logger.info(f"Deleted session '{sess['name']}' (ID: {session_id}) from database.", category="SESSIONS")
        return True

    @staticmethod
    def toggle_session(session_id: int):
        """Toggles session status between Available and Disabled."""
        sess = db.get_session(session_id)
        if not sess:
            return
        if sess.get("status") in ("Busy", "Running", "Generating"):
            raise ValueError("This session is currently in use and cannot be modified.")
            
        db.toggle_session_enabled(session_id)
        logger.info(f"Toggled enable/disable for session ID {session_id}.", category="SESSIONS")

    @staticmethod
    def update_session(session_id: int, name: str, session_type: str, cookie_data: Optional[str] = None, profile_path: Optional[str] = None):
        """Updates session metadata in database."""
        sess = db.get_session(session_id)
        if not sess:
            return
        if sess.get("status") in ("Busy", "Running", "Generating"):
            raise ValueError("This session is currently in use and cannot be modified.")

        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Session name cannot be empty.")

        db.update_session(session_id, clean_name, session_type, cookie_data, profile_path)
        logger.info(f"Updated session '{clean_name}' (ID: {session_id}).", category="SESSIONS")

    @staticmethod
    def get_masked_session_list() -> List[Dict[str, Any]]:
        """Returns sessions with sensitive cookie payloads masked for safe UI display."""
        sessions = db.get_all_sessions()
        masked = []
        for s in sessions:
            item = dict(s)
            if item.get("cookie_data"):
                item["cookie_summary"] = f"JSON Cookies ({len(item['cookie_data'])} bytes) [MASKED]"
                item["cookie_data"] = "***MASKED***"
            else:
                item["cookie_summary"] = item.get("profile_path", "N/A")
            masked.append(item)
        return masked

    @staticmethod
    def make_session_available(session_id: int):
        """Manually shifts an Expired or Failed session back to Available status."""
        db.make_session_available(session_id)
        logger.info(f"Manually shifted session ID {session_id} to Available status.", category="SESSIONS")

    @staticmethod
    def make_session_expired(session_id: int):
        """Manually shifts an Available session to Expired status."""
        db.make_session_expired(session_id)
        logger.info(f"Manually shifted session ID {session_id} to Expired status.", category="SESSIONS")

    @staticmethod
    def make_all_expired_available():
        """Manually shifts all Expired/Failed sessions back to Available status."""
        db.make_all_expired_available()
        logger.info("Manually shifted ALL expired/failed sessions to Available status.", category="SESSIONS")

    @staticmethod
    def launch_manual_browser_async(session_id: int):
        """Launches an isolated Playwright Chromium instance for a session in a background thread."""
        import threading, asyncio
        from playwright.async_api import async_playwright
        from app.automation.browser_factory import BrowserFactory

        session_info = db.get_session(session_id)
        if not session_info:
            return
        
        config = db.load_app_config()
        ext_path = config.extension_path

        def run_browser_thread():
            async def _main():
                async with async_playwright() as playwright:
                    context, page = await BrowserFactory.create_browser_context(
                        playwright=playwright,
                        session_info=session_info,
                        extension_path=ext_path,
                        headless=False
                    )
                    try:
                        await page.goto("https://www.dola.com/chat", timeout=45000, wait_until="load")
                    except Exception:
                        pass
                    logger.info(f"Manual browser session '{session_info['name']}' opened successfully.", category="SESSIONS")
                    
                    # Keep browser context open while user interacts with it
                    while len(context.pages) > 0:
                        await asyncio.sleep(1.0)

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(_main())
            except Exception as e:
                logger.error(f"Manual browser session error: {e}", category="SESSIONS")

        t = threading.Thread(target=run_browser_thread, daemon=True, name=f"ManualBrowser_{session_id}")
        t.start()

