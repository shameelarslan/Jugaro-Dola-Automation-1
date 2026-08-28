"""
Application Launcher for Waqas's Automation Software.
Initializes PyQt6 application, top-level crash logging, sys.excepthook, threading.excepthook, Queue Manager,
and Supabase Cloud User Authentication Gate.
"""

import sys
import os
import asyncio
import threading
from pathlib import Path

# Force UTF-8 encoding if console stdout is attached
if sys.stdout is not None and hasattr(sys.stdout, 'buffer'):
    try:
        import io
        if getattr(sys.stdout, 'encoding', None) != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from PyQt6.QtWidgets import QApplication, QMessageBox
from app.core.database import db
from app.core.logger import logger, log_crash
from app.core.queue_manager import QueueManager
from app.core.cloud_manager import cloud_manager
from app.gui.dialogs.auth_dialog import AuthDialog
from app.gui.main_window import MainWindow

def global_sys_excepthook(exctype, value, tb):
    """Global unhandled exception hook for PyQt application main thread."""
    log_crash("sys.excepthook (Main App Thread)", value, (exctype, value, tb))
    sys.__excepthook__(exctype, value, tb)

def global_thread_excepthook(args):
    """Global unhandled exception hook for background worker threads."""
    log_crash(f"threading.excepthook ({args.thread.name})", args.exc_value, (args.exc_type, args.exc_value, args.exc_traceback))

def global_asyncio_exception_handler(loop, context):
    """Asyncio event loop exception handler — catches Playwright subprocess and asyncio task crashes cleanly."""
    exc = context.get("exception")
    msg = context.get("message", "(no message)")

    # Ignore expected shutdown task cancellations or empty destruction notices
    if "Task was destroyed" in msg or isinstance(exc, (asyncio.CancelledError, GeneratorExit)):
        return

    if exc:
        log_crash(f"asyncio loop exception handler: {msg}", exc)
        logger.error(f"ASYNC EXCEPTION INTERCEPTED: {msg} | {exc}", category="QUEUE")
    elif msg and "(no message)" not in msg:
        logger.error(f"ASYNC EXCEPTION INTERCEPTED: {msg}", category="QUEUE")

def main():
    sys.excepthook = global_sys_excepthook
    threading.excepthook = global_thread_excepthook

    # Install global asyncio exception handler (catches Playwright subprocess crashes, asyncio task errors)
    try:
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(global_asyncio_exception_handler)
    except Exception:
        pass

    app = QApplication(sys.argv)
    
    # ── Cloud Auth Verification Gate ─────────────────────────────────────────
    if not cloud_manager.is_logged_in():
        auth_dlg = AuthDialog()
        if not auth_dlg.exec():
            sys.exit(0)

    # Check if user has been blocked by Admin
    if cloud_manager.is_blocked():
        QMessageBox.critical(
            None,
            "Account Blocked",
            "🚫 Your account has been BLOCKED by the Administrator.\nPlease contact Waqas Automation Support."
        )
        sys.exit(0)

    # Load configuration
    config = db.load_app_config()
    queue_manager = QueueManager(config)

    # Launch GUI Window
    window = MainWindow(queue_manager)
    window.show()

    def on_about_to_quit():
        """Cleanly stop automation and log on application exit."""
        try:
            queue_manager.stop_automation()
        except Exception:
            pass
        logger.info("Application closing. Goodbye.", category="SYSTEM")

    app.aboutToQuit.connect(on_about_to_quit)

    try:
        sys.exit(app.exec())
    except Exception as e:
        log_crash("QApplication.exec() Exception", e)

if __name__ == "__main__":
    main()
