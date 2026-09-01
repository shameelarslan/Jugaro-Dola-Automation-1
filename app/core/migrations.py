"""
Database Schema Migration Engine for Waqas Automation Pro.
Ensures zero data loss, idempotent schema evolution, and automatic version tracking.
"""

import sqlite3
from typing import List, Tuple
from pathlib import Path
from app.core.logger import logger

CURRENT_SCHEMA_VERSION = 5

class MigrationManager:
    """Manages SQLite schema versioning and idempotent migrations."""

    def __init__(self, db_path: str):
        self.db_path = str(db_path)

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def run_migrations(self):
        """Discovers and applies all pending database migrations in transaction."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.get_connection() as conn:
                self._ensure_migration_table(conn)
                current_ver = self._get_current_version(conn)

                if current_ver < CURRENT_SCHEMA_VERSION:
                    logger.info(f"Database schema at v{current_ver}. Applying migrations to reach v{CURRENT_SCHEMA_VERSION}...", category="DATABASE")
                    self._apply_migrations(conn, current_ver)
                    logger.info(f"✅ Database schema successfully upgraded to v{CURRENT_SCHEMA_VERSION}!", category="DATABASE")
                else:
                    logger.info(f"Database schema is up to date (v{current_ver}).", category="DATABASE")
        except Exception as e:
            logger.error(f"Migration execution error: {e}", category="DATABASE")

    def _ensure_migration_table(self, conn: sqlite3.Connection):
        """Creates the internal migration tracking table."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _schema_migrations (
                version INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

    def _get_current_version(self, conn: sqlite3.Connection) -> int:
        """Returns the highest applied schema version."""
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(version), 0) FROM _schema_migrations")
        row = cursor.fetchone()
        return row[0] if row else 0

    def _apply_migrations(self, conn: sqlite3.Connection, current_ver: int):
        """Applies migrations sequentially from current_ver + 1 to CURRENT_SCHEMA_VERSION."""
        migrations = self._get_migration_definitions()

        for ver, desc, sql_steps in migrations:
            if ver > current_ver:
                logger.info(f"Applying Migration v{ver}: {desc}...", category="DATABASE")
                cursor = conn.cursor()
                for step in sql_steps:
                    try:
                        cursor.execute(step)
                    except sqlite3.OperationalError as oe:
                        # Ignore 'duplicate column' or 'already exists' errors for idempotency
                        err_msg = str(oe).lower()
                        if "duplicate column" in err_msg or "already exists" in err_msg:
                            continue
                        raise oe
                cursor.execute("INSERT OR REPLACE INTO _schema_migrations (version, description) VALUES (?, ?)", (ver, desc))
                conn.commit()

    def _get_migration_definitions(self) -> List[Tuple[int, str, List[str]]]:
        """Returns list of (version, description, [sql statements])."""
        return [
            (
                1,
                "Core Tables Initial Schema (Settings, Batches, Sessions)",
                [
                    """CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )""",
                    """CREATE TABLE IF NOT EXISTS batches (
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
                    )""",
                    """CREATE TABLE IF NOT EXISTS sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        session_type TEXT NOT NULL,
                        cookie_data TEXT,
                        profile_path TEXT,
                        status TEXT DEFAULT 'Available',
                        credits_left INTEGER DEFAULT 4,
                        videos_left INTEGER DEFAULT 15,
                        error_count INTEGER DEFAULT 0,
                        last_used_at DATETIME,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )"""
                ]
            ),
            (
                2,
                "Add Session Credits and Videos Left Columns",
                [
                    "ALTER TABLE sessions ADD COLUMN credits_left INTEGER DEFAULT 4",
                    "ALTER TABLE sessions ADD COLUMN videos_left INTEGER DEFAULT 15",
                    "UPDATE sessions SET videos_left = 15 WHERE videos_left IS NULL",
                    "UPDATE sessions SET credits_left = 4 WHERE credits_left IS NULL"
                ]
            ),
            (
                3,
                "Prompts and Viral Prompts Tables",
                [
                    """CREATE TABLE IF NOT EXISTS prompts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        category TEXT DEFAULT 'General',
                        tags TEXT DEFAULT '',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )""",
                    """CREATE TABLE IF NOT EXISTS viral_prompts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        prompt_text TEXT NOT NULL,
                        category TEXT DEFAULT 'Viral',
                        viral_score INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )"""
                ]
            ),
            (
                4,
                "Testing & Leads Generation Engine Tables (v2.1.4+)",
                [
                    """CREATE TABLE IF NOT EXISTS leads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT,
                        phone TEXT,
                        source TEXT DEFAULT 'Organic',
                        status TEXT DEFAULT 'New',
                        lead_score INTEGER DEFAULT 50,
                        value REAL DEFAULT 0.0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )""",
                    """CREATE TABLE IF NOT EXISTS analytics_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,
                        payload TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )"""
                ]
            ),
            (
                5,
                "Indexes and Session Status Stability Hooks",
                [
                    "CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)",
                    "CREATE INDEX IF NOT EXISTS idx_batches_status ON batches(status)",
                    "CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at)",
                    "UPDATE sessions SET status = 'Available' WHERE status IN ('Busy', 'Running', 'Generating')"
                ]
            )
        ]
