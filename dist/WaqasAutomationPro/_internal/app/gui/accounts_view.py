import threading
import customtkinter as ctk

import config
from app.browser.browser_manager import BrowserManager
from app.browser.session_manager import SessionManager, SessionStatus
from app.utils.logger import log_info, log_warning, log_error

class AccountsView(ctk.CTkFrame):
    """
    Accounts Management & Session Controller View.
    Manages Facebook persistent browser session profiles for test_account_01.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.account_id = "test_account_01"

        self.grid_columnconfigure(0, weight=1)

        # Header
        lbl_title = ctk.CTkLabel(
            self,
            text="Account Session Manager",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        lbl_title.pack(padx=20, pady=(20, 10), anchor="w")

        # Account Profile Card Container
        self.card = ctk.CTkFrame(self, fg_color="#18181b", corner_radius=10)
        self.card.pack(padx=20, pady=10, fill="x")

        self.card.grid_columnconfigure(1, weight=1)

        # Account Metadata
        lbl_acc_title = ctk.CTkLabel(
            self.card,
            text="Account:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#a1a1aa"
        )
        lbl_acc_title.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        self.lbl_acc_name = ctk.CTkLabel(
            self.card,
            text=f"Test Account 01 ({self.account_id})",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#ffffff"
        )
        self.lbl_acc_name.grid(row=0, column=1, padx=10, pady=(15, 5), sticky="w")

        # Profile location
        lbl_prof_title = ctk.CTkLabel(
            self.card,
            text="Profile Dir:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#a1a1aa"
        )
        lbl_prof_title.grid(row=1, column=0, padx=20, pady=5, sticky="w")

        lbl_prof_path = ctk.CTkLabel(
            self.card,
            text=f"data/accounts/{self.account_id}/user_data/",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#71717a"
        )
        lbl_prof_path.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # Status Label
        lbl_status_title = ctk.CTkLabel(
            self.card,
            text="Status:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#a1a1aa"
        )
        lbl_status_title.grid(row=2, column=0, padx=20, pady=5, sticky="w")

        self.lbl_status = ctk.CTkLabel(
            self.card,
            text="LOGIN REQUIRED",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ef4444",
            fg_color="#3f1715",
            corner_radius=6,
            padx=10,
            pady=4
        )
        self.lbl_status.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        # Control Buttons Container
        btn_container = ctk.CTkFrame(self.card, fg_color="transparent")
        btn_container.grid(row=3, column=0, columnspan=2, padx=20, pady=(15, 20), sticky="w")

        self.btn_open_fb = ctk.CTkButton(
            btn_container,
            text="OPEN FACEBOOK",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self.on_open_facebook_clicked
        )
        self.btn_open_fb.pack(side="left", padx=(0, 10))

        self.btn_check = ctk.CTkButton(
            btn_container,
            text="CHECK SESSION",
            font=ctk.CTkFont(size=12),
            fg_color="#374151",
            hover_color="#4b5563",
            command=self.on_check_session_clicked
        )
        self.btn_check.pack(side="left")

    def update_status_ui(self, status: SessionStatus):
        """Updates GUI status badge based on SessionStatus enum."""
        if status == SessionStatus.LOGGED_IN:
            self.lbl_status.configure(
                text="LIVE",
                text_color="#10b981",
                fg_color="#064e3b"
            )
        elif status == SessionStatus.LOGIN_IN_PROGRESS:
            self.lbl_status.configure(
                text="LOGIN IN PROGRESS",
                text_color="#f59e0b",
                fg_color="#451a03"
            )
        elif status == SessionStatus.SESSION_EXPIRED:
            self.lbl_status.configure(
                text="SESSION EXPIRED",
                text_color="#f97316",
                fg_color="#431407"
            )
        elif status == SessionStatus.SESSION_ERROR:
            self.lbl_status.configure(
                text="SESSION ERROR",
                text_color="#ef4444",
                fg_color="#450a0a"
            )
        else:
            self.lbl_status.configure(
                text="LOGIN REQUIRED",
                text_color="#ef4444",
                fg_color="#3f1715"
            )

    def on_open_facebook_clicked(self):
        """Launches persistent browser and opens Facebook."""
        thread = threading.Thread(target=self._open_facebook_worker, daemon=True)
        thread.start()

    def on_check_session_clicked(self):
        """Triggers quick session check in background thread."""
        thread = threading.Thread(target=self._check_session_worker, daemon=True)
        thread.start()

    def _open_facebook_worker(self):
        self.update_status_ui(SessionStatus.LOGIN_IN_PROGRESS)

        bm = BrowserManager(
            account_id=self.account_id,
            debug_mode=True,
            window_width=500,
            window_height=600,
            slow_mo=config.DEFAULT_SLOW_MO
        )
        try:
            page = bm.launch()
            sm = SessionManager(bm)
            bm.navigate("https://www.facebook.com/")

            if not bm.wait_for_facebook_ready(timeout_seconds=30):
                self.update_status_ui(SessionStatus.SESSION_ERROR)
                log_error("[SESSION ERROR] Facebook UI not ready.", tag="SESSION")
                return

            status = sm.check_session(page)
            self.update_status_ui(status)

            if status == SessionStatus.LOGGED_IN:
                log_info("[SESSION] Session loaded successfully", tag="SESSION")
                log_info("[SESSION] Status: LIVE", tag="SESSION")
            elif status == SessionStatus.LOGIN_REQUIRED:
                log_warning("[SESSION] Login required", tag="SESSION")
                sm.wait_for_manual_login(page, status_callback=self.update_status_ui)
        except Exception as e:
            log_error(f"[SESSION ERROR] Open Facebook failed: {str(e)}", tag="SESSION")
            self.update_status_ui(SessionStatus.SESSION_ERROR)

    def _check_session_worker(self):
        bm = BrowserManager(
            account_id=self.account_id,
            debug_mode=config.DEFAULT_DEBUG_MODE,
            headless=config.DEFAULT_HEADLESS,
            window_width=config.DEFAULT_WINDOW_WIDTH,
            window_height=config.DEFAULT_WINDOW_HEIGHT
        )
        try:
            page = bm.launch()
            sm = SessionManager(bm)
            bm.navigate("https://www.facebook.com/")
            if bm.wait_for_facebook_ready(timeout_seconds=30):
                status = sm.check_session(page)
                self.update_status_ui(status)
            else:
                self.update_status_ui(SessionStatus.SESSION_ERROR)
            bm.close()
        except Exception as e:
            log_error(f"[SESSION ERROR] Check failed: {str(e)}", tag="SESSION")
            self.update_status_ui(SessionStatus.SESSION_ERROR)
            if bm:
                bm.close()
