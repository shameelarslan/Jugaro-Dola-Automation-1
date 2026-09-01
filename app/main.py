"""
Application Launcher for Waqas's Automation Software.
Initializes application, top-level crash logging, sys.excepthook, threading.excepthook, Queue Manager,
and Supabase Cloud User Authentication Gate.
Launches the Modern Commercial SaaS Web Desktop Interface (Edge WebView2 / PyWebView) with PyQt6 fallback.
"""

import sys
import os
import time
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
    """Global unhandled exception hook for main thread."""
    log_crash("sys.excepthook (Main App Thread)", value, (exctype, value, tb))
    sys.__excepthook__(exctype, value, tb)

def global_thread_excepthook(args):
    """Global unhandled exception hook for background worker threads."""
    log_crash(f"threading.excepthook ({args.thread.name})", args.exc_value, (args.exc_type, args.exc_value, args.exc_traceback))

def global_asyncio_exception_handler(loop, context):
    """Asyncio event loop exception handler — catches Playwright subprocess and asyncio task crashes cleanly."""
    exc = context.get("exception")
    msg = context.get("message", "(no message)")

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

    try:
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(global_asyncio_exception_handler)
    except Exception:
        pass

    from app.core.version import get_installed_version, APP_NAME
    _v = get_installed_version()
    logger.info(f"⚡ [BOOT CHECK] {APP_NAME} v{_v} DISK MODULE ACTIVE & EXECUTING!", category="SYSTEM")
    
    # ── Launch Sidecar Web/REST API Server on port 8765 ──────────────────────
    try:
        from app.server import run_server
        server_thread = threading.Thread(target=run_server, args=(8765,), daemon=True)
        server_thread.start()
        time.sleep(0.5)
    except Exception as e:
        logger.error(f"Could not start background web server: {e}", category="SYSTEM")

    # ── Cloud Auth Verification Gate ─────────────────────────────────────────
    # Check if user has been blocked by Admin
    if cloud_manager.is_blocked():
        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(
            None,
            "Account Blocked",
            "🚫 Your account has been BLOCKED by the Administrator.\nPlease contact Waqas Automation Support."
        )
        sys.exit(0)

    # ── Launch Modes ─────────────────────────────────────────────────────────
    # Mode A: Explicit PyQt6 Native GUI requested
    if any(arg in sys.argv for arg in ["--gui", "--qt", "--legacy"]):
        logger.info("🖥️ Launching PyQt6 Native Desktop GUI...", category="SYSTEM")
        app = QApplication.instance() or QApplication(sys.argv)
        config = db.load_app_config()
        queue_manager = QueueManager(config)

        window = MainWindow(queue_manager)
        window.show()

        def on_about_to_quit():
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
            return

    # Mode B: Server-only (Headless)
    if any(arg in sys.argv for arg in ["--server-only", "--headless", "--no-gui"]):
        logger.info("🌐 Waqas Automation Pro Server is active at: http://127.0.0.1:8765", category="SYSTEM")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("⏹️ Server stopped cleanly by user.", category="SYSTEM")
        return

    # Mode C: Default Native Desktop Window (PyWebView with Edge WebView2 Engine)
    web_url = "http://127.0.0.1:8765"
    logger.info("🖥️ Launching Native Standalone Desktop Application Window...", category="SYSTEM")
    
    desktop_launched = False
    try:
        import webview
        # Brief pause to ensure local server is ready
        time.sleep(0.4)
        
        # Create full native standalone desktop application window
        window = webview.create_window(
            title=f"Waqas Automation Pro v{_v}",
            url=web_url,
            width=1360,
            height=860,
            min_size=(1080, 700),
            background_color="#0f172a",
            easy_drag=False
        )
        desktop_launched = True
        webview.start(gui="edgechromium", debug=False)
        sys.exit(0)
    except Exception as e:
        logger.warning(f"PyWebView native window launch encountered issue: {e}. Launching PyQt6 GUI fallback...", category="SYSTEM")

    # Fallback 1: PyQt6 Desktop GUI
    if not desktop_launched:
        try:
            app = QApplication.instance() or QApplication(sys.argv)
            config = db.load_app_config()
            queue_manager = QueueManager(config)
            window = MainWindow(queue_manager)
            window.show()
            sys.exit(app.exec())
        except Exception as e:
            logger.error(f"PyQt6 fallback failed: {e}. Opening default browser as last resort.", category="SYSTEM")
            import webbrowser
            webbrowser.open(web_url)
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass

if __name__ == "__main__":
    main()
