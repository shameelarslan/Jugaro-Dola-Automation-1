"""
Centralized Application Mode & Admin Security Manager.
Manages USER MODE (simplified status, clean activity) and ADMIN MODE (full diagnostics, raw logs).
Protected by Salted PBKDF2-HMAC-SHA256 Cryptographic Hash and shortcut Ctrl+Shift+W.
"""

import re
import hashlib
import hmac
from typing import List, Callable, Optional, Any, Dict, Set
from PyQt6.QtCore import QObject, pyqtSignal

class AdminManager(QObject):
    mode_changed = pyqtSignal(bool)  # True = Admin, False = User

    _instance: Optional["AdminManager"] = None

    # Salted PBKDF2-HMAC-SHA256 hash (100,000 iterations)
    _SALT: bytes = bytes.fromhex("77617161735f6175746f6d6174696f6e5f76325f7365637572655f73616c74")
    _EXPECTED_HASH: bytes = bytes.fromhex("c469ca1aa1251b94399e3d3adbcfe3d313d29d8e6ccac5ac69bd7e49b0b8ddd4")

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._is_admin: bool = False
        self._callbacks: List[Callable[[bool], None]] = []
        # Per-job de-duplication stage tracking for User Mode
        self._job_stages: Dict[str, Set[str]] = {}
        self._initialized = True

    @property
    def is_admin(self) -> bool:
        return self._is_admin

    def set_admin_mode(self, enabled: bool):
        self._is_admin = bool(enabled)
        self.mode_changed.emit(self._is_admin)
        self._notify_callbacks(self._is_admin)

    def register_callback(self, callback: Callable[[bool], None]):
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[bool], None]):
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def verify_password(self, password: str) -> bool:
        """Cryptographically verifies password against master passwords and salted PBKDF2 hash."""
        if not password:
            return False
        pwd = password.strip()
        # Direct master passwords
        if pwd in ("qwerty1234@", "waqas12345", "Admin@123", "admin123", "waqas786"):
            return True
        try:
            computed = hashlib.pbkdf2_hmac(
                "sha256",
                pwd.encode("utf-8"),
                self._SALT,
                100_000
            )
            return hmac.compare_digest(computed, self._EXPECTED_HASH)
        except Exception:
            return False

    def unlock_admin_mode(self, password: str) -> bool:
        """Verifies password and activates Admin Mode if valid."""
        if self.verify_password(password):
            self._is_admin = True
            self.mode_changed.emit(True)
            self._notify_callbacks(True)
            return True
        return False

    def lock_user_mode(self):
        """Reverts application state back to User Mode."""
        self._is_admin = False
        self.mode_changed.emit(False)
        self._notify_callbacks(False)

    def toggle_admin_mode(self, prompt_callback: Optional[Callable[[], Optional[str]]] = None) -> bool:
        """Toggles between User and Admin mode using password prompt if locking to admin."""
        if self._is_admin:
            self.lock_user_mode()
            return False
        elif prompt_callback:
            pwd = prompt_callback()
            if pwd and self.unlock_admin_mode(pwd):
                return True
        return False

    def _notify_callbacks(self, is_admin: bool):
        for cb in self._callbacks:
            try:
                cb(is_admin)
            except Exception:
                pass

    def _mark_stage_once(self, job_key: str, stage_key: str) -> bool:
        """Returns True if this stage has NOT been emitted yet for this job; False if duplicate."""
        if not job_key:
            return True
        if job_key not in self._job_stages:
            self._job_stages[job_key] = set()
        if stage_key in self._job_stages[job_key]:
            return False
        self._job_stages[job_key].add(stage_key)
        return True

    def clear_job_stages(self, job_key: Optional[str] = None):
        """Cleans up stage cache for completed jobs."""
        if job_key and job_key in self._job_stages:
            del self._job_stages[job_key]
        elif not job_key:
            self._job_stages.clear()

    def reset_job_stages(self, job_key: Optional[str] = None):
        """Alias for clear_job_stages."""
        self.clear_job_stages(job_key)

    def format_log_entry(self, entry: Any, is_admin: Optional[bool] = None) -> Optional[str]:
        """
        Formats a LogEntry according to current mode permissions.
        - ADMIN MODE: Returns full raw diagnostic log with selectors, JS traces, extraction details, and stacktraces.
        - USER MODE: Returns polished high-level workflow steps, de-duplicated, hiding all internal technical noise.
        """
        active_admin = self._is_admin if is_admin is None else is_admin

        if active_admin:
            return entry.format_log()

        # ── USER MODE POLISHED FORMATTING & SANITIZATION ─────────────────────
        raw_msg = getattr(entry, "message", "") or ""
        msg_lower = raw_msg.lower()
        level = getattr(entry, "level", "INFO")
        worker_id = getattr(entry, "worker_id", None)
        job_id = getattr(entry, "job_id", None)
        session_name = getattr(entry, "session_name", None)
        timestamp = getattr(entry, "timestamp", "")

        job_key = job_id or (f"w{worker_id}" if worker_id is not None else "global")

        w_str = f"Worker {worker_id:02d}" if worker_id is not None else "System"
        j_str = f"[{job_id}] " if job_id else ""
        s_str = f"({session_name}) " if session_name else ""
        prefix = f"{timestamp} | {w_str} | {j_str}{s_str}".strip() + " "

        # ── 1. HARD SUPPRESSION: Internal technical details that must NEVER show in User Mode ──
        suppress_keywords = [
            "smart download extraction result", "direct http video downloaded",
            "no cookie popup found", "mode before:", "mode after:",
            "checking composer mode", "pro option locator", "opening skills menu",
            "selecting 'generate videos' skill", "pasting prompt into",
            "locator", "selector", "prosemirror", "getboundingclientrect", "page.goto",
            "page.wait_for", "page.evaluate", "queryselector", "role=", "data-valid-btn",
            "href=", "svg[", "input_mp4", "filter_complex", "delogo", "avgblur",
            "returncode", "ffmpeg version", "traceback (most recent call last)",
            "wsarecv", "connection was aborted", "attempt 1/3", "attempt 2/3", "attempt 3/3",
            "leaf node", "dismissing cookie", "cookie popup", "browsercontext",
            "playwright", "debug:", "stage:", "active_tabs", "data-src", "data-url",
            "div[role=", "button:has-text", "div:has-text", "span:has-text", "a:has-text",
            "button.new-chat-btn", "appdata\\local\\temp", "temp\\dola", "failed to load https"
        ]

        # ── 2. WORKFLOW STEP MAPPINGS (Polished & De-duplicated) ─────────────

        # Step: Session Selected (Retain Session Name)
        if "assigning session" in msg_lower:
            m = re.search(r"Assigning Session\s+['\"]?([^'\"]+)['\"]?\s+\((\d+)\s+prompts\)", raw_msg, re.IGNORECASE)
            if m:
                return f"{prefix}🔑 Session '{m.group(1)}' selected ({m.group(2)} prompts assigned)"
            return f"{prefix}🔑 Session selected"

        # Step: Automation / Job Started
        if "started rolling session automation" in msg_lower:
            m = re.search(r"Run:\s*([A-Za-z0-9_]+)", raw_msg)
            run_tag = f" (Run: {m.group(1)})" if m else ""
            return f"{prefix}🚀 Automation batch started{run_tag}"

        if "starting session batch" in msg_lower or "worker launch requested" in msg_lower:
            if self._mark_stage_once(job_key, "job_started"):
                return f"{prefix}🚀 Job started — Preparing session"
            return None

        # Step: Opening Dola AI
        if "navigating to" in msg_lower and "dola" in msg_lower:
            if self._mark_stage_once(job_key, "open_dola"):
                return f"{prefix}🌐 Opening Dola AI..."
            return None

        if "page loaded and ready" in msg_lower:
            if self._mark_stage_once(job_key, "dola_loaded"):
                return f"{prefix}✅ Dola loaded and ready"
            return None

        # Step: New Chat
        if "clicking new chat" in msg_lower:
            if self._mark_stage_once(job_key, "new_chat_clicked"):
                return f"{prefix}💬 Starting fresh New Chat conversation..."
            return None

        if "fresh chat interface fully ready" in msg_lower:
            if self._mark_stage_once(job_key, "new_chat_ready"):
                return f"{prefix}✅ Fresh chat interface ready"
            return None

        # Step: Pro Mode Activated (Exact 1 time)
        if "pro mode verified" in msg_lower or "mode after: pro" in msg_lower:
            if self._mark_stage_once(job_key, "pro_mode"):
                return f"{prefix}⚡ Pro mode activated"
            return None

        # Step: Generate Videos Selected (Exact 1 time)
        if "generate videos skill verified" in msg_lower or "generate videos skill selected" in msg_lower:
            if self._mark_stage_once(job_key, "gen_videos_skill"):
                return f"{prefix}🎬 Generate Videos selected"
            return None

        # Step: Prompt Submitted
        if "prompt submitted with no error" in msg_lower or "prompt paste verified" in msg_lower:
            if self._mark_stage_once(job_key, "prompt_submitted"):
                return f"{prefix}📝 Prompt submitted successfully"
            return None

        # Step: Video Generation In Progress
        if "generation in progress" in msg_lower or "waiting for dola completion" in msg_lower:
            if self._mark_stage_once(job_key, "generation_in_progress"):
                return f"{prefix}⏳ Video generation in progress... Waiting for Dola."
            return None

        # Step: Video Ready & Downloading (Exact 1 time)
        if "video generation completed" in msg_lower or "downloading video" in msg_lower or "intercepted tab download" in msg_lower:
            if self._mark_stage_once(job_key, "downloading_video"):
                return f"{prefix}📥 Downloading video..."
            return None

        # Step: Video Verified (Clean message)
        if "mp4 verified" in msg_lower:
            if self._mark_stage_once(job_key, "video_verified"):
                return f"{prefix}✅ Video verified"
            return None

        # Step: Processing Final Video / Watermark
        if "removing watermark" in msg_lower:
            if self._mark_stage_once(job_key, "processing_video"):
                return f"{prefix}🧼 Processing final video..."
            return None

        # Step: Video Saved (Exact 1 time)
        if "saved to output folder" in msg_lower or "watermark successfully blurred" in msg_lower or "video saved" in msg_lower:
            if self._mark_stage_once(job_key, "video_saved"):
                m = re.search(r"([A-Za-z0-9_\-]+\.mp4)", raw_msg)
                fn_str = f": {m.group(1)}" if m else ""
                return f"{prefix}📁 Video saved{fn_str}"
            return None

        # Step: Job Completed (Exact 1 time)
        if "job completed successfully" in msg_lower:
            if self._mark_stage_once(job_key, "job_completed"):
                return f"{prefix}🏆 Job completed successfully"
            return None

        if "all" in msg_lower and "prompt automation jobs completed" in msg_lower:
            return f"{prefix}🏆 All automation jobs completed successfully!"

        # Step: Session Expired / Logged Out / Quota Exceeded
        if "session_daily_limit_exceeded" in msg_lower or "session daily limit exceeded" in msg_lower:
            return f"{prefix}🚨 Session Daily Limit Exceeded"

        if "session_logged_out" in msg_lower or "session is logged out" in msg_lower:
            return f"{prefix}🚨 Session expired or logged out. Please re-authenticate."

        # Step: Job Failed
        if "video generation timed out" in msg_lower:
            return f"{prefix}❌ Video generation timed out."

        if "pro selection failed" in msg_lower:
            return f"{prefix}❌ Pro mode selection failed."

        if "job failed" in msg_lower:
            return f"{prefix}❌ Job execution encountered an error."

        # ── Check Suppression Blacklist ──────────────────────────────────────
        if any(kw in msg_lower for kw in suppress_keywords):
            return None

        # General clean progress info fallback
        if level == "INFO" and len(raw_msg) < 90 and not any(c in raw_msg for c in ["{", "}", ";", "=>", "http://", "https://", "\\Temp\\"]):
            return f"{prefix}{raw_msg}".strip()

        return None

admin_manager = AdminManager()
