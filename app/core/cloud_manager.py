"""
Supabase Cloud Manager - Multi-User Authentication & Real-Time SaaS Analytics.
Includes Role-Based Access Control (Admin, Paid, Free) and Admin Approval System.
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
ADMIN_EMAILS = {"waqasshoukat2193@gmail.com", "ali@gmail.com", "shameel@gmail.com", "waqasai@gmail.com"}
try:
    from app.core.updater import get_installed_version
    APP_VERSION = get_installed_version()
except Exception:
    APP_VERSION = "2.0.7"


class CloudManager:
    _instance: Optional["CloudManager"] = None

    def __init__(self):
        self.client: Optional[Client] = None
        self.current_user: Optional[Dict[str, Any]] = None
        self._super_stats_cache: Optional[Dict[str, Any]] = None
        self._super_stats_last_fetch: float = 0.0
        self._user_stats_cache: Optional[Dict[str, Any]] = None
        self._user_stats_last_fetch: float = 0.0
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

    def determine_role(self, email: str, profile_role: str = "") -> str:
        """Determines user role: 'admin', 'paid', or 'free'."""
        email_clean = email.strip().lower()
        if email_clean in [e.lower() for e in ADMIN_EMAILS] or (profile_role and profile_role.lower() == "admin"):
            return "admin"
        if profile_role and profile_role.lower() in ("paid", "pro", "premium"):
            return "paid"
        return "free"

    def _load_saved_session(self):
        """Loads cached session from disk on startup."""
        if not SESSION_FILE.exists():
            return
        try:
            with open(SESSION_FILE, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            if data and "access_token" in data and self.client:
                user_id = data.get("user_id")
                email = data.get("email")
                full_name = data.get("full_name", "")
                status = data.get("status", "Pending")
                saved_role = data.get("role", "")

                profile_role = saved_role
                # Verify live status & role from Supabase
                try:
                    res = self.client.table("profiles").select("*").eq("id", user_id).execute()
                    if res.data and len(res.data) > 0:
                        profile = res.data[0]
                        status = profile.get("status", status)
                        full_name = profile.get("full_name", full_name)
                        profile_role = profile.get("role", saved_role)
                except Exception:
                    pass

                role = self.determine_role(email, profile_role)

                self.current_user = {
                    "id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "status": status,
                    "role": role,
                    "access_token": data.get("access_token")
                }

                # Auto-sync admin mode
                try:
                    from app.core.admin_manager import admin_manager
                    admin_manager.set_admin_mode(role == "admin")
                except Exception:
                    pass

                logger.info(f"Loaded cloud user session: {email} (Role: {role.upper()}, Status: {status})", category="CLOUD")
        except Exception as e:
            logger.warning(f"Error loading saved cloud session: {e}", category="CLOUD")

    def _save_session(self, user_id: str, email: str, full_name: str, status: str, role: str, access_token: str):
        """Saves session data to disk."""
        try:
            SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "user_id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "status": status,
                    "role": role,
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
            initial_role = "admin" if email_clean in [e.lower() for e in ADMIN_EMAILS] else "free"

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
                # Ensure profile exists with correct initial status & role
                try:
                    self.client.table("profiles").upsert({
                        "id": user_id,
                        "email": email_clean,
                        "full_name": full_name,
                        "status": initial_status,
                        "role": initial_role,
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
                        "role": initial_role,
                        "access_token": access_token
                    }
                    self._save_session(user_id, email_clean, full_name, "Active", initial_role, access_token)
                    
                    try:
                        from app.core.admin_manager import admin_manager
                        admin_manager.set_admin_mode(initial_role == "admin")
                    except Exception:
                        pass

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
        """Authenticates user with Supabase and enforces Role-Based Access."""
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
                profile_role = "admin" if email_clean in [e.lower() for e in ADMIN_EMAILS] else "free"
                full_name = email_clean.split("@")[0].capitalize()

                if prof_res.data and len(prof_res.data) > 0:
                    status = prof_res.data[0].get("status", status)
                    profile_role = prof_res.data[0].get("role", profile_role)
                    full_name = prof_res.data[0].get("full_name") or full_name
                else:
                    # Create if missing
                    try:
                        self.client.table("profiles").insert({
                            "id": user_id,
                            "email": email_clean,
                            "full_name": full_name,
                            "status": status,
                            "role": profile_role
                        }).execute()
                    except Exception:
                        pass

                # Check Approval Status
                if status == "Pending":
                    return False, "⏳ ACCOUNT PENDING APPROVAL\n\nYour account has been registered, but is waiting for Admin Approval.\nPlease contact Admin Waqas to activate your access."

                if status == "Blocked":
                    return False, "🚫 ACCOUNT BLOCKED\n\nYour access has been disabled by the Administrator."

                role = self.determine_role(email_clean, profile_role)
                access_token = getattr(res.session, "access_token", "") if res.session else ""
                
                self.current_user = {
                    "id": user_id,
                    "email": email_clean,
                    "full_name": full_name,
                    "status": "Active",
                    "role": role,
                    "access_token": access_token
                }
                self._save_session(user_id, email_clean, full_name, "Active", role, access_token)
                
                # Auto-sync admin mode for role == "admin"
                try:
                    from app.core.admin_manager import admin_manager
                    admin_manager.set_admin_mode(role == "admin")
                except Exception:
                    pass

                self._user_stats_cache = None
                self._super_stats_cache = None
                logger.info(f"User logged in: {email_clean} (Role: {role.upper()})", category="CLOUD")
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
        self._user_stats_cache = None
        self._super_stats_cache = None
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
        try:
            from app.core.admin_manager import admin_manager
            admin_manager.set_admin_mode(False)
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
            res = self.client.table("profiles").select("status, role").eq("id", self.current_user["id"]).execute()
            if res.data and len(res.data) > 0:
                cur_status = res.data[0].get("status", "Pending")
                cur_role = res.data[0].get("role", self.current_user.get("role", "free"))
                self.current_user["status"] = cur_status
                self.current_user["role"] = self.determine_role(self.current_user["email"], cur_role)
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
            self._user_stats_cache = None
            self._super_stats_cache = None
            return True
        except Exception as e:
            logger.warning(f"Failed to push cloud video activity: {e}", category="CLOUD")
            return False

    def fetch_user_dashboard_stats(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetches personalized telemetry, daily generation counts and recent activity for currently logged-in user."""
        now = time.time()
        if not force_refresh and self._user_stats_cache and (now - self._user_stats_last_fetch < 3.0):
            return self._user_stats_cache

        if not self.current_user:
            return {
                "total_videos": 0,
                "today_videos": 0,
                "daily_activity": {},
                "recent_activity": []
            }

        user_id = str(self.current_user.get("id") or self.current_user.get("user_id") or "")
        user_email = (self.current_user.get("email") or "").strip().lower()

        if not self.client:
            return {
                "total_videos": 0,
                "today_videos": 0,
                "daily_activity": {},
                "recent_activity": []
            }

        try:
            now_utc = datetime.now(timezone.utc)
            today_start = datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=timezone.utc)
            today_date_str = today_start.strftime("%Y-%m-%d")

            # Query video_activity for this specific user
            query = self.client.table("video_activity").select("id, video_name, created_at, status, file_size_mb")
            if user_id and user_email:
                query = query.or_(f"user_id.eq.{user_id},user_email.eq.{user_email}")
            elif user_id:
                query = query.eq("user_id", user_id)
            elif user_email:
                query = query.eq("user_email", user_email)

            res = query.order("created_at", desc=True).limit(1000).execute()
            rows = res.data or []

            total_videos = len(rows)
            today_videos = 0
            daily_activity = {}

            for r in rows:
                c_str = r.get("created_at", "")
                if c_str:
                    d_key = c_str.split("T")[0] if "T" in c_str else c_str[:10]
                    if d_key:
                        daily_activity[d_key] = daily_activity.get(d_key, 0) + 1

                try:
                    dt = datetime.fromisoformat(c_str.replace("Z", "+00:00"))
                    if dt >= today_start:
                        today_videos += 1
                except Exception:
                    if c_str.startswith(today_date_str):
                        today_videos += 1

            result = {
                "total_videos": total_videos,
                "today_videos": today_videos,
                "daily_activity": daily_activity,
                "recent_activity": rows[:20]
            }
            self._user_stats_cache = result
            self._user_stats_last_fetch = time.time()
            return result
        except Exception as e:
            logger.warning(f"Failed to fetch user dashboard stats: {e}", category="CLOUD")
            return {
                "total_videos": 0,
                "today_videos": 0,
                "daily_activity": {},
                "recent_activity": []
            }

    def fetch_super_dashboard_stats(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetches full aggregated multi-user analytics & profiles for Super Admin (5s Cache)."""
        now = time.time()
        if not force_refresh and self._super_stats_cache and (now - self._super_stats_last_fetch < 5.0):
            return self._super_stats_cache

        if not self.client:
            return self._super_stats_cache or {
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
            prof_res = self.client.table("profiles").select("*").order("created_at", desc=True).execute()
            profiles = prof_res.data or []

            total_users = len(profiles)
            pending_users = len([p for p in profiles if p.get("status") == "Pending"])

            try:
                tot_cnt_res = self.client.table("video_activity").select("id", count="exact").limit(1).execute()
                total_videos_all_time = tot_cnt_res.count if tot_cnt_res.count is not None else 0
            except Exception as e:
                total_videos_all_time = 0

            now_utc = datetime.now(timezone.utc)
            today_start = datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=timezone.utc)
            today_start_iso = today_start.isoformat()

            try:
                tdy_cnt_res = self.client.table("video_activity").select("id", count="exact").gte("created_at", today_start_iso).limit(1).execute()
                today_videos = tdy_cnt_res.count if tdy_cnt_res.count is not None else 0
            except Exception as e:
                today_videos = 0

            user_total_counts = {}
            user_today_counts = {}
            user_daily_activity = {}  # { key: { "YYYY-MM-DD": count } }
            user_active_dates = {}     # { key: set("YYYY-MM-DD") }
            user_last_active = {}      # { key: ISO string }
            daily_summary = {}         # { "YYYY-MM-DD": { "videos": int, "active_users": set() } }
            active_user_ids_today = set()

            # 1. Register active logins from profiles
            for prof in profiles:
                p_uid = str(prof.get("id") or "")
                p_email = (prof.get("email") or "").strip().lower()
                p_key = p_uid or p_email
                if not p_key:
                    continue

                if p_key not in user_active_dates:
                    user_active_dates[p_key] = set()

                p_last = prof.get("last_active_at") or prof.get("created_at") or ""
                if p_last:
                    user_last_active[p_key] = p_last
                    d_key = p_last.split("T")[0] if "T" in p_last else p_last[:10]
                    if d_key:
                        user_active_dates[p_key].add(d_key)
                        if d_key not in daily_summary:
                            daily_summary[d_key] = {"videos": 0, "active_users": set()}
                        daily_summary[d_key]["active_users"].add(p_key)
                        if p_uid:
                            daily_summary[d_key]["active_users"].add(p_uid)
                        if p_email:
                            daily_summary[d_key]["active_users"].add(p_email)

            # 2. Register video activity generations
            page = 0
            page_size = 1000
            while True:
                act_page = self.client.table("video_activity").select("user_id, user_email, created_at").order("created_at", desc=True).range(page * page_size, (page + 1) * page_size - 1).execute()
                rows = act_page.data or []
                if not rows:
                    break
                for act in rows:
                    uid = str(act.get("user_id") or "")
                    u_email = (act.get("user_email") or "").strip().lower()
                    key = uid or u_email
                    if not key:
                        continue

                    user_total_counts[key] = user_total_counts.get(key, 0) + 1
                    created_str = act.get("created_at", "")
                    
                    if key not in user_last_active and created_str:
                        user_last_active[key] = created_str

                    if created_str:
                        date_key = created_str.split("T")[0] if "T" in created_str else created_str[:10]
                        if date_key:
                            if key not in user_daily_activity:
                                user_daily_activity[key] = {}
                            user_daily_activity[key][date_key] = user_daily_activity[key].get(date_key, 0) + 1

                            if key not in user_active_dates:
                                user_active_dates[key] = set()
                            user_active_dates[key].add(date_key)

                            if date_key not in daily_summary:
                                daily_summary[date_key] = {"videos": 0, "active_users": set()}
                            daily_summary[date_key]["videos"] += 1
                            daily_summary[date_key]["active_users"].add(key)
                            if uid:
                                daily_summary[date_key]["active_users"].add(uid)
                            if u_email:
                                daily_summary[date_key]["active_users"].add(u_email)

                    try:
                        dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                        if dt >= today_start:
                            if uid:
                                active_user_ids_today.add(uid)
                            user_today_counts[key] = user_today_counts.get(key, 0) + 1
                    except Exception:
                        pass
                if len(rows) < page_size:
                    break
                page += 1

            today_date_str = today_start_iso.split("T")[0]
            # Also ensure users with last_active_at today are counted in active_users_today
            for prof in profiles:
                p_last = prof.get("last_active_at") or ""
                if p_last and p_last.startswith(today_date_str):
                    p_uid = str(prof.get("id") or "")
                    if p_uid:
                        active_user_ids_today.add(p_uid)

            recent_res = self.client.table("video_activity").select("*").order("created_at", desc=True).limit(30).execute()
            activities = recent_res.data or []
            active_users_today = len(active_user_ids_today)

            # Format daily summary for JSON (convert sets to counts)
            formatted_daily_summary = {}
            for d_key, d_val in daily_summary.items():
                formatted_daily_summary[d_key] = {
                    "videos": d_val["videos"],
                    "active_users_count": len(d_val["active_users"])
                }

            all_users = []
            for prof in profiles:
                uid = str(prof.get("id") or "")
                u_email = (prof.get("email") or "").strip().lower()
                tot = user_total_counts.get(uid) or user_total_counts.get(u_email, 0)
                tdy = user_today_counts.get(uid) or user_today_counts.get(u_email, 0)
                u_daily = user_daily_activity.get(uid) or user_daily_activity.get(u_email, {})
                last_act = prof.get("last_active_at") or user_last_active.get(uid) or user_last_active.get(u_email, "") or prof.get("created_at", "")
                user_role = self.determine_role(u_email, prof.get("role", ""))

                u_act_dates = list((user_active_dates.get(uid, set()) | user_active_dates.get(u_email, set())))

                # Calculate smart lead & activity tag
                is_active_today = (today_date_str in u_act_dates) or (tdy > 0)
                if is_active_today:
                    lead_tag = "Daily Active"
                elif tot >= 50:
                    lead_tag = "High Producer"
                elif tot >= 10:
                    lead_tag = "Active Creator"
                elif tot > 0:
                    lead_tag = "Low Activity"
                else:
                    lead_tag = "Inactive Lead"

                all_users.append({
                    "user_id": uid,
                    "name": prof.get("full_name") or (u_email.split("@")[0].capitalize() if u_email else "Creator"),
                    "email": prof.get("email", ""),
                    "whatsapp_number": prof.get("whatsapp_number", ""),
                    "total_videos": tot,
                    "today_videos": tdy,
                    "daily_activity": u_daily,
                    "active_dates": u_act_dates,
                    "last_active_at": last_act,
                    "lead_tag": lead_tag,
                    "status": prof.get("status", "Pending"),
                    "role": user_role,
                    "created_at": prof.get("created_at", "")
                })

            all_users.sort(key=lambda x: (0 if x["status"] == "Pending" else 1, -x["total_videos"]))
            for idx, item in enumerate(all_users):
                item["rank"] = idx + 1

            res_dict = {
                "total_users": total_users,
                "pending_users": pending_users,
                "total_videos_all_time": total_videos_all_time,
                "today_videos": today_videos,
                "active_users_today": active_users_today,
                "daily_summary": formatted_daily_summary,
                "top_creators": [u for u in all_users if u["status"] == "Active"][:15],
                "all_users": all_users,
                "recent_activity": activities
            }
            self._super_stats_cache = res_dict
            self._super_stats_last_fetch = time.time()
            return res_dict
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
        """Updates user status ('Active', 'Pending', or 'Blocked') in Supabase."""
        if not self.client:
            return False
        try:
            self.client.rpc("admin_update_user_status", {
                "target_user_id": user_id,
                "new_status": new_status
            }).execute()
            logger.info(f"User {user_id} status updated to: {new_status}", category="CLOUD")
            return True
        except Exception:
            try:
                self.client.table("profiles").update({"status": new_status}).eq("id", user_id).execute()
                logger.info(f"User {user_id} status updated to: {new_status} (direct)", category="CLOUD")
                return True
            except Exception as e:
                logger.error(f"Failed to update user status: {e}", category="CLOUD")
                return False

    def update_user_role(self, user_id: str, new_role: str) -> bool:
        """Updates user role ('admin', 'paid', or 'free') in Supabase."""
        if not self.client:
            return False
        role_clean = new_role.strip().lower()
        if role_clean not in ("admin", "paid", "free"):
            role_clean = "free"
        try:
            self.client.rpc("admin_update_user_role", {
                "target_user_id": user_id,
                "new_role": role_clean
            }).execute()
            logger.info(f"User {user_id} role updated to: {role_clean}", category="CLOUD")
            return True
        except Exception:
            try:
                self.client.table("profiles").update({"role": role_clean}).eq("id", user_id).execute()
                logger.info(f"User {user_id} role updated to: {role_clean} (direct)", category="CLOUD")
                return True
            except Exception as e:
                logger.error(f"Failed to update user role: {e}", category="CLOUD")
                return False

    def check_for_update(self) -> Optional[Dict[str, Any]]:
        """Checks Supabase for available updates targeted at current user.
        Returns update info dict if update available, None otherwise."""
        if not self.client or not self.current_user:
            return None
        try:
            user_email = (self.current_user.get("email") or "").strip().lower()
            user_role = self.current_user.get("role", "")
            # Fetch latest active releases from app_releases table
            res = self.client.table("app_releases") \
                .select("*") \
                .eq("is_active", True) \
                .order("id", desc=True) \
                .execute()

            if not res.data:
                return None

            applicable_release = None
            for update in res.data:
                target = (update.get("target_email") or "*").strip().lower()
                if target and target != "*":
                    target_list = [e.strip().lower() for e in target.replace(";", ",").split(",") if e.strip()]
                    # Direct email match always passes (even if "admin" is also in the list)
                    if user_email in target_list:
                        pass  # explicitly allowed
                    elif "admin" in target_list:
                        if self.determine_role(user_email, user_role) != "admin":
                            continue
                    else:
                        continue
                applicable_release = update
                break

            if not applicable_release:
                return None

            latest_version = applicable_release.get("version", "").strip()

            from app.core.updater import _is_newer_semver, get_installed_version
            curr_ver = get_installed_version()
            if not _is_newer_semver(latest_version, curr_ver):
                return None

            logger.info(f"Update available: v{latest_version} for {user_email}", category="CLOUD")
            return {
                "version": latest_version,
                "download_url": applicable_release.get("download_url", ""),
                "release_notes": applicable_release.get("changelog", ""),
                "is_mandatory": applicable_release.get("is_mandatory", False),
                "current_version": curr_ver
            }
        except Exception as e:
            logger.warning(f"Update check failed: {e}", category="CLOUD")
            return None

cloud_manager = CloudManager.get_instance()
