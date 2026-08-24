"""
SQLite Database Storage and CRUD Engine for Dola Bulk Automation.
Handles persistence for settings, sessions, prompts, batches, jobs, and execution history.
"""

import os
import json
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from app.core.config import DB_PATH, DEFAULT_DOWNLOAD_DIR, AppConfig
from app.core.logger import logger

class DatabaseManager:
    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize SQLite database tables and indexes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Settings Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # 2. Batches Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batches (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    preset_name TEXT,
                    output_folder TEXT NOT NULL,
                    separate_batch_folders INTEGER DEFAULT 1,
                    concurrency_limit INTEGER DEFAULT 5,
                    status TEXT DEFAULT 'Created',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    started_at DATETIME,
                    completed_at DATETIME
                )
            """)

            # 3. Sessions Table (PERMANENT STORAGE)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    session_type TEXT NOT NULL,
                    cookie_data TEXT,
                    profile_path TEXT,
                    status TEXT DEFAULT 'Available',
                    credits_left INTEGER DEFAULT 4,
                    error_count INTEGER DEFAULT 0,
                    last_used_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Add credits_left column if missing in existing database
            try:
                cursor.execute("ALTER TABLE sessions ADD COLUMN credits_left INTEGER DEFAULT 4")
            except Exception:
                pass

            # STABILITY RECOVERY: On app startup, reset stale runtime statuses ('Busy', 'Running', 'Generating') back to 'Available'
            cursor.execute("""
                UPDATE sessions
                SET status = 'Available'
                WHERE status IN ('Busy', 'Running', 'Generating')
            """)

            # 24-HOUR ROLLING COOLDOWN RESET: Automatically revert 'Expired' sessions back to 'Available' if 24 hours have passed since last used
            cursor.execute("""
                UPDATE sessions
                SET status = 'Available', credits_left = 4
                WHERE status = 'Expired'
                  AND (last_used_at IS NULL OR datetime(last_used_at, '+24 hours') <= datetime('now', 'localtime'))
            """)

            # 4. Prompts Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt_text TEXT NOT NULL,
                    ratio TEXT DEFAULT '9:16',
                    duration INTEGER DEFAULT 10,
                    model TEXT DEFAULT 'Seedance 2.0',
                    status TEXT DEFAULT 'Pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 5. Jobs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    batch_id TEXT NOT NULL,
                    prompt_id INTEGER NOT NULL,
                    session_id INTEGER NOT NULL,
                    worker_id INTEGER,
                    status TEXT DEFAULT 'Pending',
                    retry_count INTEGER DEFAULT 0,
                    downloaded_filename TEXT,
                    downloaded_filepath TEXT,
                    downloaded_filesize INTEGER,
                    error_message TEXT,
                    stage_at_failure TEXT,
                    started_at DATETIME,
                    completed_at DATETIME,
                    FOREIGN KEY(batch_id) REFERENCES batches(id) ON DELETE CASCADE,
                    FOREIGN KEY(prompt_id) REFERENCES prompts(id) ON DELETE CASCADE,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            """)

            conn.commit()

    # ==========================================
    # Settings CRUD
    # ==========================================
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """, (key, value))
            conn.commit()

    def load_app_config(self) -> AppConfig:
        config = AppConfig()
        raw = self.get_setting("app_config")
        if raw:
            try:
                data = json.loads(raw)
                for k, v in data.items():
                    if hasattr(config, k):
                        setattr(config, k, v)
            except Exception as e:
                logger.error(f"Error parsing app config from DB: {e}")
        
        return config

    def save_app_config(self, config: AppConfig):
        self.set_setting("app_config", json.dumps(config.to_dict()))

    # ==========================================
    # Sessions CRUD
    # ==========================================
    def add_session(self, name: str, session_type: str, cookie_data: Optional[str] = None, profile_path: Optional[str] = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (name, session_type, cookie_data, profile_path, status)
                VALUES (?, ?, ?, ?, 'Available')
            """, (name, session_type, cookie_data, profile_path))
            conn.commit()
            return cursor.lastrowid



    def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions ORDER BY id ASC")
            return [dict(r) for r in cursor.fetchall()]

    def update_session(self, session_id: int, name: str, session_type: str, cookie_data: Optional[str] = None, profile_path: Optional[str] = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions
                SET name = ?, session_type = ?, cookie_data = COALESCE(?, cookie_data), profile_path = COALESCE(?, profile_path)
                WHERE id = ?
            """, (name, session_type, cookie_data, profile_path, session_id))
            conn.commit()

    def toggle_session_enabled(self, session_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            if row:
                current = row["status"]
                if current == "Disabled":
                    new_status = "Available"
                elif current in ("Available", "Failed"):
                    new_status = "Disabled"
                else:
                    return # Do not toggle if Busy
                cursor.execute("UPDATE sessions SET status = ? WHERE id = ?", (new_status, session_id))
                conn.commit()

    def update_session_status(self, session_id: int, status: str, error_count_delta: int = 0):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                UPDATE sessions
                SET status = ?, error_count = MAX(0, error_count + ?), last_used_at = ?
                WHERE id = ?
            """, (status, error_count_delta, now, session_id))
            conn.commit()

    def make_session_expired(self, session_id: int):
        """Explicitly sets session status to Expired and clears active state."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                UPDATE sessions
                SET status = 'Expired', last_used_at = ?
                WHERE id = ?
            """, (now, session_id))
            conn.commit()

    def reset_expired_sessions(self):
        """Restores Expired sessions back to Available status with 4 credits once their individual 24-hour cooldown has elapsed."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, last_used_at FROM sessions
                    WHERE status = 'Expired'
                      AND (last_used_at IS NULL OR datetime(last_used_at, '+24 hours') <= datetime('now', 'localtime'))
                """)
                ready_sessions = cursor.fetchall()
                if ready_sessions:
                    for s in ready_sessions:
                        cursor.execute("""
                            UPDATE sessions
                            SET status = 'Available', credits_left = 4
                            WHERE id = ?
                        """, (s["id"],))
                        logger.info(f"🔄 24-Hour Cooldown Elapsed: Restored session '{s['name']}' to Available (4 credits).", category="DATABASE")
                    conn.commit()
        except Exception as e:
            logger.warning(f"Error checking 24-hour session reset: {e}", category="DATABASE")

    def make_session_available(self, session_id: int):
        """Manually shifts an Expired or Failed session back to Available status."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE sessions SET status = 'Available', credits_left = 4 WHERE id = ?", (session_id,))
            conn.commit()

    def make_session_expired(self, session_id: int):
        """Manually shifts an Available session to Expired status."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("UPDATE sessions SET status = 'Expired', last_used_at = ? WHERE id = ?", (now_str, session_id))
            conn.commit()

    def make_all_expired_available(self):
        """Manually shifts ALL Expired or Failed sessions back to Available status."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE sessions SET status = 'Available' WHERE status IN ('Expired', 'Failed')")
            conn.commit()

    def update_session_credits(self, session_id: int, credits_left: int):
        """Updates remaining Dola credits for a session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE sessions SET credits_left = ? WHERE id = ?", (credits_left, session_id))
            conn.commit()

    def delete_session(self, session_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()

    # ==========================================
    # Prompts CRUD
    # ==========================================
    def add_prompt(self, prompt_text: str, ratio: str = "9:16", duration: int = 10, model: str = "Seedance 2.0") -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO prompts (prompt_text, ratio, duration, model)
                VALUES (?, ?, ?, ?)
            """, (prompt_text, ratio, duration, model))
            conn.commit()
            return cursor.lastrowid

    def get_all_prompts(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM prompts ORDER BY id ASC")
            return [dict(r) for r in cursor.fetchall()]

    def get_pending_prompts(self) -> List[Dict[str, Any]]:
        """Returns all prompts that do not currently have a Completed job."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.* FROM prompts p
                WHERE p.id NOT IN (
                    SELECT prompt_id FROM jobs WHERE status = 'Completed'
                )
                ORDER BY p.id ASC
            """)
            return [dict(r) for r in cursor.fetchall()]

    def get_prompt(self, prompt_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_prompt(self, prompt_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs WHERE prompt_id = ?", (prompt_id,))
            cursor.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
            conn.commit()

    def clear_all_prompts(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs WHERE prompt_id IS NOT NULL")
            cursor.execute("DELETE FROM prompts")
            conn.commit()

    # ==========================================
    # Batches & Jobs CRUD
    # ==========================================
    def create_batch(self, batch_id: str, name: str, preset_name: str, output_folder: str,
                     separate_batch_folders: bool = True, concurrency_limit: int = 5) -> str:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO batches (id, name, preset_name, output_folder, separate_batch_folders, concurrency_limit, status)
                VALUES (?, ?, ?, ?, ?, ?, 'Created')
            """, (batch_id, name, preset_name, output_folder, 1 if separate_batch_folders else 0, concurrency_limit))
            conn.commit()
            return batch_id

    def get_batch(self, batch_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM batches WHERE id = ?", (batch_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_batches(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM batches ORDER BY created_at DESC")
            return [dict(r) for r in cursor.fetchall()]

    def update_batch_status(self, batch_id: str, status: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if status == "Running":
                cursor.execute("UPDATE batches SET status = ?, started_at = ? WHERE id = ?", (status, now, batch_id))
            elif status in ("Completed", "Failed", "Stopped"):
                cursor.execute("UPDATE batches SET status = ?, completed_at = ? WHERE id = ?", (status, now, batch_id))
            else:
                cursor.execute("UPDATE batches SET status = ? WHERE id = ?", (status, batch_id))
            conn.commit()

    def add_job(self, job_id: str, batch_id: str, prompt_id: int, session_id: int) -> str:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO jobs (id, batch_id, prompt_id, session_id, status)
                VALUES (?, ?, ?, ?, 'Pending')
            """, (job_id, batch_id, prompt_id, session_id))
            conn.commit()
            return job_id

    def update_job_status(self, job_id: str, status: str, worker_id: Optional[int] = None,
                          error_message: Optional[str] = None, stage_at_failure: Optional[str] = None,
                          file_path: Optional[str] = None, file_size: Optional[int] = None,
                          downloaded_filename: Optional[str] = None, downloaded_filepath: Optional[str] = None,
                          downloaded_filesize: Optional[int] = None, **kwargs):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            updates = ["status = ?"]
            params = [status]
            
            if worker_id is not None:
                updates.append("worker_id = ?")
                params.append(worker_id)
            if status in ("Starting", "Generating", "GENERATING", "DOWNLOADING"):
                updates.append("started_at = COALESCE(started_at, ?)")
                params.append(now)
            if status in ("Completed", "Failed"):
                updates.append("completed_at = ?")
                params.append(now)
            if status == "Completed":
                self.increment_lifetime_videos_count(1)
            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)
            if stage_at_failure is not None:
                updates.append("stage_at_failure = ?")
                params.append(stage_at_failure)

            # Handle both filepath parameter names
            final_filepath = downloaded_filepath or file_path
            if final_filepath:
                updates.append("downloaded_filepath = ?")
                params.append(final_filepath)

            # Handle downloaded_filename or derive from filepath
            final_filename = downloaded_filename or (os.path.basename(final_filepath) if final_filepath else None)
            if final_filename:
                updates.append("downloaded_filename = ?")
                params.append(final_filename)

            # Handle file_size / downloaded_filesize
            final_filesize = downloaded_filesize if downloaded_filesize is not None else file_size
            if final_filesize is not None:
                updates.append("downloaded_filesize = ?")
                params.append(final_filesize)

            params.append(job_id)
            sql = f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(sql, params)
            conn.commit()

    def retry_failed_jobs(self) -> int:
        """
        Resets all 'Failed' jobs back to 'Pending' while preserving their assigned session_id.
        Also sets their assigned session status back to 'Available' so the automation queue can re-run them cleanly.
        Returns the count of retried jobs.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT session_id FROM jobs WHERE status = 'Failed'")
            failed_sessions = [r["session_id"] for r in cursor.fetchall() if r["session_id"]]

            for sess_id in failed_sessions:
                cursor.execute("UPDATE sessions SET status = 'Available' WHERE id = ?", (sess_id,))

            cursor.execute("""
                UPDATE jobs
                SET status = 'Pending', error_message = NULL, stage_at_failure = NULL, worker_id = NULL
                WHERE status = 'Failed'
            """)
            count = cursor.rowcount
            conn.commit()
            return count

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT j.*, p.prompt_text, s.name as session_name
                FROM jobs j
                LEFT JOIN prompts p ON j.prompt_id = p.id
                LEFT JOIN sessions s ON j.session_id = s.id
                WHERE j.id = ?
            """, (job_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT j.*, p.prompt_text, s.name as session_name
                FROM jobs j
                JOIN prompts p ON j.prompt_id = p.id
                JOIN sessions s ON j.session_id = s.id
                ORDER BY j.rowid DESC
            """)
            return [dict(r) for r in cursor.fetchall()]

    def get_batch_jobs(self, batch_id: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT j.*, p.prompt_text, s.name as session_name
                FROM jobs j
                JOIN prompts p ON j.prompt_id = p.id
                JOIN sessions s ON j.session_id = s.id
                WHERE j.batch_id = ?
                ORDER BY j.id ASC
            """, (batch_id,))
            return [dict(r) for r in cursor.fetchall()]

    def reset_failed_jobs(self, batch_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE jobs
                SET status = 'Pending', retry_count = 0, error_message = NULL, stage_at_failure = NULL
                WHERE batch_id = ? AND status = 'Failed'
            """, (batch_id,))
            conn.commit()

    def get_lifetime_videos_count(self) -> int:
        """Returns the persistent cumulative count of all generated & downloaded videos across time."""
        val = self.get_setting("lifetime_videos_generated", default=None)
        if val is None:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM jobs WHERE status = 'Completed'")
                row = cur.fetchone()
                count = row[0] if row else 0
                self.set_setting("lifetime_videos_generated", str(count))
                return count
        try:
            return int(val)
        except Exception:
            return 0

    def increment_lifetime_videos_count(self, delta: int = 1) -> int:
        """Increments the persistent cumulative lifetime videos count."""
        current = self.get_lifetime_videos_count()
        new_count = current + delta
        self.set_setting("lifetime_videos_generated", str(new_count))
        return new_count

    def clear_all_jobs(self):
        """Deletes all jobs and batches from SQLite database without resetting lifetime statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs")
            cursor.execute("DELETE FROM batches")
            conn.commit()

# Global database singleton
db = DatabaseManager()
