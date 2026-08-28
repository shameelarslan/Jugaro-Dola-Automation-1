import sqlite3
from config import DB_PATH
from app.utils.logger import log_info, log_error

class Database:
    """
    SQLite Database Manager using standard library sqlite3.
    """
    def __init__(self, db_path=DB_PATH):
        self.db_path = str(db_path)
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Creates tables for accounts, pages, jobs, and execution logs."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS accounts (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        fb_user_id TEXT,
                        profile_dir TEXT NOT NULL,
                        status TEXT DEFAULT 'LIVE',
                        last_activity TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pages (
                        id TEXT PRIMARY KEY,
                        account_id TEXT NOT NULL,
                        page_name TEXT NOT NULL,
                        page_id TEXT,
                        page_url TEXT,
                        status TEXT DEFAULT 'ACTIVE',
                        FOREIGN KEY (account_id) REFERENCES accounts(id)
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS jobs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_id TEXT NOT NULL,
                        page_id TEXT NOT NULL,
                        video_path TEXT NOT NULL,
                        status TEXT DEFAULT 'PENDING',
                        scheduled_at TEXT,
                        published_at TEXT,
                        log_output TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                log_info(f"Database initialized cleanly at {self.db_path}", tag="DATABASE")
        except Exception as e:
            log_error(f"Failed to initialize database: {str(e)}", tag="DATABASE")
            raise e

    def get_metrics(self):
        """Returns metric totals for GUI Dashboard."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM accounts")
                total_accounts = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM accounts WHERE status='LIVE'")
                live_accounts = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM accounts WHERE status='DEAD'")
                dead_accounts = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM pages WHERE status='ACTIVE'")
                active_pages = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM jobs WHERE status='PENDING'")
                pending_videos = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM jobs WHERE status='PUBLISHED'")
                published_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM jobs WHERE status='FAILED'")
                failed_count = cursor.fetchone()[0]

                return {
                    "total_accounts": total_accounts,
                    "live_accounts": live_accounts,
                    "dead_accounts": dead_accounts,
                    "active_pages": active_pages,
                    "pending_videos": pending_videos,
                    "published": published_count,
                    "failed": failed_count,
                }
        except Exception as e:
            log_error(f"Error fetching DB metrics: {str(e)}", tag="DATABASE")
            return {
                "total_accounts": 0,
                "live_accounts": 0,
                "dead_accounts": 0,
                "active_pages": 0,
                "pending_videos": 0,
                "published": 0,
                "failed": 0,
            }

db = Database()
