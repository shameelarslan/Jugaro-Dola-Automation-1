import threading
import customtkinter as ctk
from app.gui.components.stat_card import StatCard
from app.gui.components.log_panel import LogPanel
from app.storage.database import db
from app.browser.browser_manager import BrowserManager
from app.utils.logger import log_info, log_error

class DashboardView(ctk.CTkFrame):
    """
    Main Dashboard View.
    Displays metrics summary & embedded live log panel.
    Provides quick browser test button.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Title Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")

        lbl_title = ctk.CTkLabel(
            header,
            text="System Overview & Control",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        lbl_title.pack(side="left")

        btn_test_browser = ctk.CTkButton(
            header,
            text="Test Browser Launch",
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.run_browser_test_thread
        )
        btn_test_browser.pack(side="right")

        # Stats Cards Grid Container
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        for col in range(7):
            stats_frame.grid_columnconfigure(col, weight=1)

        self.card_total_acc = StatCard(stats_frame, title="Total Accs", value="0", color="#3b82f6")
        self.card_total_acc.grid(row=0, column=0, padx=4, pady=4, sticky="ew")

        self.card_live_acc = StatCard(stats_frame, title="Live Accs", value="0", color="#10b981")
        self.card_live_acc.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

        self.card_dead_acc = StatCard(stats_frame, title="Dead Accs", value="0", color="#ef4444")
        self.card_dead_acc.grid(row=0, column=2, padx=4, pady=4, sticky="ew")

        self.card_pages = StatCard(stats_frame, title="Active Pages", value="0", color="#8b5cf6")
        self.card_pages.grid(row=0, column=3, padx=4, pady=4, sticky="ew")

        self.card_pending = StatCard(stats_frame, title="Pending Vids", value="0", color="#f59e0b")
        self.card_pending.grid(row=0, column=4, padx=4, pady=4, sticky="ew")

        self.card_published = StatCard(stats_frame, title="Published", value="0", color="#10b981")
        self.card_published.grid(row=0, column=5, padx=4, pady=4, sticky="ew")

        self.card_failed = StatCard(stats_frame, title="Failed", value="0", color="#ef4444")
        self.card_failed.grid(row=0, column=6, padx=4, pady=4, sticky="ew")

        # Log Panel
        self.log_panel = LogPanel(self)
        self.log_panel.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="nsew")

        self.refresh_metrics()

    def refresh_metrics(self):
        metrics = db.get_metrics()
        self.card_total_acc.update_value(metrics["total_accounts"])
        self.card_live_acc.update_value(metrics["live_accounts"])
        self.card_dead_acc.update_value(metrics["dead_accounts"])
        self.card_pages.update_value(metrics["active_pages"])
        self.card_pending.update_value(metrics["pending_videos"])
        self.card_published.update_value(metrics["published"])
        self.card_failed.update_value(metrics["failed"])

    def run_browser_test_thread(self):
        """Runs browser test in background worker thread to keep GUI responsive."""
        thread = threading.Thread(target=self._browser_test_worker, daemon=True)
        thread.start()

    def _browser_test_worker(self):
        log_info("Starting independent Browser Launch test from GUI...", tag="GUI_TEST")
        try:
            bm = BrowserManager(
                account_id="gui_test_account",
                debug_mode=True,
                window_width=400,
                window_height=400,
                slow_mo=300
            )
            page = bm.launch()
            bm.navigate("https://www.facebook.com")
            page.wait_for_timeout(3000)
            log_info(f"[SUCCESS] Browser loaded URL: {page.url}", tag="GUI_TEST")
            bm.close()
            log_info("[SUCCESS] Browser launch test completed successfully.", tag="GUI_TEST")
        except Exception as e:
            log_error(f"[FAILED] Browser test error: {str(e)}", tag="GUI_TEST")
