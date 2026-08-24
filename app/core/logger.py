"""
Thread-safe, sanitized structured logging engine with PyQt event stream callbacks.
"""

import re
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Any
from app.core.config import DATA_DIR

def _safe_print(text: str) -> None:
    """Print to stdout safely — replaces any character that cannot be encoded by the terminal."""
    if sys.stdout is None:
        return
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except UnicodeEncodeError:
        # Fallback: encode to terminal codec with replacement, then decode back
        try:
            enc = getattr(sys.stdout, 'encoding', None) or 'utf-8'
            safe = text.encode(enc, errors='replace').decode(enc, errors='replace')
            sys.stdout.write(safe + "\n")
            sys.stdout.flush()
        except Exception:
            pass
    except Exception:
        pass

LOGS_DIR = DATA_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
MAIN_LOG_FILE = LOGS_DIR / "dola_automation.log"
CRASH_LOG_FILE = LOGS_DIR / "crash.log"

def log_crash(origin: str, exc: Any, exc_info=None):
    """Logs full traceback to crash.log persistent file and application error log."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if exc_info:
        tb_str = "".join(traceback.format_exception(*exc_info))
    elif isinstance(exc, Exception):
        tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    else:
        tb_str = str(exc)

    crash_entry = (
        f"========================================================\n"
        f"CRASH / UNHANDLED EXCEPTION DETECTED AT {now_str}\n"
        f"Origin: {origin}\n"
        f"Exception: {exc}\n"
        f"Traceback:\n{tb_str}\n"
        f"========================================================\n\n"
    )

    try:
        with open(CRASH_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(crash_entry)
            f.flush()
    except Exception:
        pass

    _safe_print(crash_entry)

# Regex patterns to sanitize sensitive tokens/cookies
COOKIE_PATTERN = re.compile(r'(?i)(session|cookie|token|auth|bearer|key)=["\']?[^"\'\s;&]+["\']?')

def sanitize_message(msg: str) -> str:
    """Mask raw cookie strings or authentication tokens before logging."""
    if not msg:
        return ""
    return COOKIE_PATTERN.sub(r'\1=***MASKED***', str(msg))

class LogEntry:
    def __init__(self, timestamp: str, level: str, category: str, message: str,
                 worker_id: Optional[int] = None, job_id: Optional[str] = None, session_name: Optional[str] = None):
        self.timestamp = timestamp
        self.level = level
        self.category = category
        self.message = sanitize_message(message)
        self.worker_id = worker_id
        self.job_id = job_id
        self.session_name = session_name

    def format_log(self) -> str:
        w_str = f"Worker {self.worker_id:02d}" if self.worker_id is not None else "System"
        j_str = f"[{self.job_id}]" if self.job_id else ""
        s_str = f"({self.session_name})" if self.session_name else ""
        return f"{self.timestamp} | {self.level:<5} | {w_str} | {j_str} {s_str} {self.message}".strip()

class AppLogger:
    def __init__(self):
        self._listeners: List[Callable[[LogEntry], None]] = []
        self._file_handle = open(MAIN_LOG_FILE, "a", encoding="utf-8")
        self.history: List[LogEntry] = []

    def get_recent_entries(self, limit: int = 200) -> List[str]:
        return [e.format_log() for e in self.history[-limit:]]


    def register_listener(self, callback: Callable[[LogEntry], None]):
        """Register a callback for UI live streaming (e.g. PyQt signal)."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def unregister_listener(self, callback: Callable[[LogEntry], None]):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def register_callback(self, callback: Callable[[LogEntry], None]):
        """Register callback alias for register_listener."""
        self.register_listener(callback)

    def unregister_callback(self, callback: Callable[[LogEntry], None]):
        """Unregister callback alias for unregister_listener."""
        self.unregister_listener(callback)

    def _log(self, level: str, category: str, message: str,
             worker_id: Optional[int] = None, job_id: Optional[str] = None, session_name: Optional[str] = None):
        now_str = datetime.now().strftime("%H:%M:%S")
        entry = LogEntry(
            timestamp=now_str,
            level=level,
            category=category,
            message=message,
            worker_id=worker_id,
            job_id=job_id,
            session_name=session_name
        )
        self.history.append(entry)
        if len(self.history) > 1000:
            self.history = self.history[-500:]

        formatted = entry.format_log()

        
        # Write to file
        try:
            self._file_handle.write(formatted + "\n")
            self._file_handle.flush()
        except Exception:
            pass

        # Print to stdout safely (handles Windows cp1252 terminal encoding)
        _safe_print(formatted)

        # Notify UI listeners
        for listener in self._listeners:
            try:
                listener(entry)
            except Exception:
                pass

    def info(self, message: str, category: str = "GENERAL", worker_id: Optional[int] = None, job_id: Optional[str] = None, session_name: Optional[str] = None):
        self._log("INFO", category, message, worker_id, job_id, session_name)

    def warning(self, message: str, category: str = "GENERAL", worker_id: Optional[int] = None, job_id: Optional[str] = None, session_name: Optional[str] = None):
        self._log("WARN", category, message, worker_id, job_id, session_name)

    def error(self, message: str, category: str = "GENERAL", worker_id: Optional[int] = None, job_id: Optional[str] = None, session_name: Optional[str] = None):
        self._log("ERROR", category, message, worker_id, job_id, session_name)

    def debug(self, message: str, category: str = "GENERAL", worker_id: Optional[int] = None, job_id: Optional[str] = None, session_name: Optional[str] = None):
        self._log("DEBUG", category, message, worker_id, job_id, session_name)

# Global logger singleton instance
logger = AppLogger()
