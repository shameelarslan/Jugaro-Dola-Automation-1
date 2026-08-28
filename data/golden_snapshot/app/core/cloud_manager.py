"""
Supabase Cloud Manager - Multi-User Authentication & Real-Time SaaS Analytics.
Includes Admin Approval System for 100% spam/fake account protection.
"""

import os
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from app.core.logger import logger

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = Any

SUPABASE_URL = "https://krdclqrlxbwpnadfxudd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtyZGNscXJseGJ3cG5hZGZ4dWRkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY4MjA5MDcsImV4cCI6MjEwMjM5NjkwN30.8W956EAIwjV_V43k5x7-SX7IsfTYoz_74HIMEJ9kwnQ"

SESSION_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "user_session.json"
ADMIN_EMAILS = {"waqasshoukat2193@gmail.com", "ali@gmail.com"}
ADMIN_EMAIL = "waqasshoukat2193@gmail.com"

class CloudManager:
    _instance: Optional["CloudManager"] = None

    def __init__(self):
        self.client: Optional[Client] = None
        self.current_user: Optional[Dict[str, Any]] = None
        self._init_client()
        self._load_saved_session()

    @classmethod
    def get_instance(cls) -> "CloudManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _init_client(self):
        if create_client:
            try:
                self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}", category="CLOUD")
                self.client = None

    def _load_saved_session(self):
        """Loads cached session from disk on startup."""
        if not SESSION_FILE.exists():
            return
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data and "access_token" in data and self.client:
                user_id = data.get("user_id")
                email = data.get("email")
                full_name = data.get("full_name", "")
                status = data.get("status", "Pending")

                # Verify live status from Supabase
                try:
                    res = self.client.table("profiles").select("*").eq("id", user_id).execute()
                    if res.data and len(res.data) > 0:
                        profile = res.data[0]
                        status = profile.get("status", status)
                        full_name = profile.get("full_name", full_name)
                except Exception:
                    pass

                self.current_user = {
                    "id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "status": status,
                    "access_token": data.get("access_token")
                }
                logger.info(f"Loaded cloud user session: {email} (Status: {status})", category="CLOUD")
        except Exception as e:
            logger.warning(f"Error loading saved cloud session: {e}", category="CLOUD")

    def _save_session(self, user_id: str, email: str, full_name: str, status: str, access_token: str):
        """Saves session data to disk."""
        try:
            SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "user_id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "status": status,
                    "access_token": access_token
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving cloud session: {e}", category="CLOUD")

    def signup(self, email: str, password: str, full_name: str = "", whatsapp_number: str = "") -> Tuple[bool, str, str]:
        """
        Registers a new user on Supabase.
        Returns: (success: bool, message: str, status: str)
        """
        if not self.client:
            return False, "Supabase connection is not available.", ""
        try:
            email_clean = email.strip().lower()
            full_name = full_name.strip() or email_clean.split("@")[0].capitalize()
            whatsapp_clean = whatsapp_number.strip()
            initial_status = "Active" if email_clean in [e.lower() for e in ADMIN_EMAILS] else "Pending"

            res = self.client.auth.sign_up({
                "email": email_clean,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name
                    }
                }
            })
            if res.user:
                user_id = str(res.user.id)
                # Ensure profile exists with correct initial status
                try:
                    self.client.table("profiles").upsert({
                        "id": user_id,
                        "email": email_clean,
                        "full_name": full_name,
                        "status": initial_status,
                        "whatsapp_number": whatsapp_clean
                    }).execute()
                except Exception:
                    pass

                access_token = getattr(res.session, "access_token", "") if res.session else ""
                
                if initial_status == "Active":
                    self.current_user = {
                        "id": user_id,
                        "email": email_clean,
                        "full_name": full_name,
                        "status": "Active",
                        "access_token": access_token
                    }
                    self._save_session(user_id, email_clean, full_name, "Active", access_token)
                    return True, "Admin account registered and activated!", "Active"
                else:
                    return True, "🎉 Account created! Your account is currently PENDING Admin Approval. Please contact Admin Waqas to activate your access.", "Pending"

            return False, "Registration failed: No user returned.", ""
        except Exception as e:
            err_msg = str(e)
            if "already registered" in err_msg.lower():
                err_msg = "This email is already registered. Please Sign In."
            logger.error(f"Signup error: {e}", category="CLOUD")
            return False, err_msg, ""

    def login(self, email: str, password: str) -> Tuple[bool, str]:
        """Authenticates user with Supabase and enforces Admin Approval."""
        if not self.client:
            return False, "Supabase connection is not available."
        try:
            email_clean = email.strip().lower()
            res = self.client.auth.sign_in_with_password({
                "email": email_clean,
                "password": password
            })
            if res.user:
                user_id = str(res.user.id)
                # Fetch profile details
                prof_res = self.client.table("profiles").select("*").eq("id", user_id).execute()
                status = "Active" if email_clean in [e.lower() for e in ADMIN_EMAILS] else "Pending"
                full_name = email_clean.split("@")[0].capitalize()

                if prof_res.data and len(prof_res.data) > 0:
                    status = prof_res.data[0].get("status", status)
                    full_name = prof_res.data[0].get("full_name") or full_name
                else:
                    # Create if missing
                    try:
                        self.client.table("profiles").insert({
                            "id": user_id,
                            "email": email_clean,
                            "full_name": full_name,
                            "status": status
                        }).execute()
                    except Exception:
                        pass

                # Check Approval Status
                if status == "Pending":
                    return False, "⏳ ACCOUNT PENDING APPROVAL\n\nYour account has been registered, but is waiting for Admin Approval.\nPlease contact Admin Waqas to activate your access."

                if status == "Blocked":
                    return False, "🚫 ACCOUNT BLOCKED\n\nYour access has been disabled by the Administrator."

                access_token = getattr(res.session, "access_token", "") if res.session else ""
                self.current_user = {
                    "id": user_id,
                    "email": email_clean,
                    "full_name": full_name,
                    "status": "Active",
                    "access_token": access_token
                }
                self._save_session(user_id, email_clean, full_name, "Active", access_token)
                logger.info(f"User logged in successfully: {email_clean}", category="CLOUD")
                return True, "Login successful!"
            return False, "Invalid email or password."
        except Exception as e:
            err_msg = str(e)
            if "invalid login credentials" in err_msg.lower():
                err_msg = "Invalid email or password."
            logger.error(f"Login error: {e}", category="CLOUD")
            return False, err_msg

    def logout(self):
        """Clears local user session."""
        self.current_user = None
        if SESSION_FILE.exists():
            try:
                os.remove(SESSION_FILE)
            except Exception:
                pass
        if self.client:
            try:
                self.client.auth.sign_out()
            except Exception:
                pass
        logger.info("User logged out cleanly.", category="CLOUD")

    def is_logged_in(self) -> bool:
        return self.current_user is not None and self.current_user.get("status") == "Active"

    def is_approved(self) -> bool:
        """Verifies if current user status is still Active in Supabase."""
        if not self.current_user or not self.client:
            return False
        try:
            res = self.client.table("profiles").select("status").eq("id", self.current_user["id"]).execute()
            if res.data and len(res.data) > 0:
                cur_status = res.data[0].get("status", "Pending")
                self.current_user["status"] = cur_status
                return cur_status == "Active"
        except Exception:
            pass
        return self.current_user.get("status") == "Active"

    def is_blocked(self) -> bool:
        """Verifies if current user status is Blocked in Supabase."""
        if not self.current_user or not self.client:
            return False
        try:
            res = self.client.table("profiles").select("status").eq("id", self.current_user["id"]).execute()
            if res.data and len(res.data) > 0:
                cur_status = res.data[0].get("status", "Pending")
                self.current_user["status"] = cur_status
                return cur_status == "Blocked"
        except Exception:
            pass
        return self.current_user.get("status") == "Blocked"

    def log_video_event(self, video_name: str, file_size_mb: float = 0.0) -> bool:
        """Pushes video completion telemetry to Supabase."""
        if not self.client or not self.current_user:
            return False
        try:
            payload = {
                "user_id": self.current_user["id"],
                "user_email": self.current_user["email"],
                "video_name": video_name,
                "status": "Completed",
                "file_size_mb": round(file_size_mb, 2)
            }
            self.client.table("video_activity").insert(payload).execute()
            logger.info(f"Cloud Activity Synced: {self.current_user['email']} generated {video_name}", category="CLOUD")
            return True
        except Exception as e:
            logger.warning(f"Failed to push cloud video activity: {e}", category="CLOUD")
            return False

    def fetch_super_dashboard_stats(self) -> Dict[str, Any]:
        """Fetches full aggregated multi-user analytics & pending requests for Super Admin."""
        if not self.client:
            return {
                "total_users": 0,
                "pending_users": 0,
                "total_videos_all_time": 0,
                "today_videos": 0,
                "active_users_today": 0,
                "top_creators": [],
                "recent_activity": [],
                "all_users": []
            }
        try:
            # 1. Fetch all profiles
            prof_res = self.client.table("profiles").select("*").order("created_at", desc=True).execute()
            profiles = prof_res.data or []

            # 2. Fetch all video activity
            act_res = self.client.table("video_activity").select("*").order("created_at", desc=True).limit(1000).execute()
            activities = act_res.data or []

            total_users = len(profiles)
            pending_users = len([p for p in profiles if p.get("status") == "Pending"])
            total_videos_all_time = len(activities)

            # Calculate today's cutoff in UTC
            now_utc = datetime.now(timezone.utc)
            today_start = datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=timezone.utc)

            today_activities = []
            active_user_ids_today = set()

            user_total_counts = {}
            user_today_counts = {}

            for act in activities:
                uid = act.get("user_id") or act.get("user_email")
                user_total_counts[uid] = user_total_counts.get(uid, 0) + 1

                created_str = act.get("created_at", "")
                try:
                    dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                    if dt >= today_start:
                        today_activities.append(act)
                        if act.get("user_id"):
                            active_user_ids_today.add(act.get("user_id"))
                        user_today_counts[uid] = user_today_counts.get(uid, 0) + 1
                except Exception:
                    pass

            today_videos = len(today_activities)
            active_users_today = len(active_user_ids_today)

            # Build Full User List with ranks & statuses
            all_users = []
            for prof in profiles:
                uid = prof.get("id")
                u_email = prof.get("email")
                tot = user_total_counts.get(uid, 0) + user_total_counts.get(u_email, 0)
                tdy = user_today_counts.get(uid, 0) + user_today_counts.get(u_email, 0)

                all_users.append({
                    "user_id": uid,
                    "name": prof.get("full_name") or u_email.split("@")[0].capitalize(),
                    "email": u_email,
                    "whatsapp_number": prof.get("whatsapp_number", ""),
                    "total_videos": tot,
                    "today_videos": tdy,
                    "status": prof.get("status", "Pending"),
                    "created_at": prof.get("created_at", "")
                })

            # Sort: Pending users first, then by total_videos DESC
            all_users.sort(key=lambda x: (0 if x["status"] == "Pending" else 1, -x["total_videos"]))
            for idx, item in enumerate(all_users):
                item["rank"] = idx + 1

            return {
                "total_users": total_users,
                "pending_users": pending_users,
                "total_videos_all_time": total_videos_all_time,
                "today_videos": today_videos,
                "active_users_today": active_users_today,
                "top_creators": [u for u in all_users if u["status"] == "Active"][:15],
                "all_users": all_users,
                "recent_activity": activities[:30]
            }
        except Exception as e:
            logger.error(f"Error fetching super dashboard stats: {e}", category="CLOUD")
            return {
                "total_users": 0,
                "pending_users": 0,
                "total_videos_all_time": 0,
                "today_videos": 0,
                "active_users_today": 0,
                "top_creators": [],
                "recent_activity": [],
                "all_users": []
            }

    def toggle_user_status(self, user_id: str, new_status: str) -> bool:
        """Updates user status ('Active', 'Pending', or 'Blocked') in Supabase.
        Uses SECURITY DEFINER RPC function to bypass RLS restrictions."""
        if not self.client:
            return False
        try:
            # Primary: Use RPC function (SECURITY DEFINER bypasses RLS)
            self.client.rpc("admin_update_user_status", {
                "target_user_id": user_id,
                "new_status": new_status
            }).execute()
            logger.info(f"User {user_id} status updated to: {new_status} (via RPC)", category="CLOUD")
            return True
        except Exception as rpc_err:
            logger.warning(f"RPC status update failed, trying direct update: {rpc_err}", category="CLOUD")
            try:
                # Fallback: Direct table update (works if auth session is active)
                self.client.table("profiles").update({"status": new_status}).eq("id", user_id).execute()
                logger.info(f"User {user_id} status updated to: {new_status} (via direct update)", category="CLOUD")
                return True
            except Exception as e:
                logger.error(f"Failed to update user status: {e}", category="CLOUD")
                return False

cloud_manager = CloudManager.get_instance()
