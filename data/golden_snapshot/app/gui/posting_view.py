import threading
import customtkinter as ctk

import config
from app.automation.state_machine import StateMachine
from app.utils.logger import log_info, log_error

class PostingView(ctk.CTkFrame):
    """
    Posting & Automation Runner View.
    Triggers State Machine engine for verified Page Switching and Identity Verification.
    Stops safely at PAGE_CONTEXT_VERIFIED without proceeding to Reel upload.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.account_id = "test_account_01"
        self.target_page = "Huang"

        self.grid_columnconfigure(0, weight=1)

        # Header
        lbl_title = ctk.CTkLabel(
            self,
            text="Automation Pipeline & Page Switcher Runner",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        lbl_title.pack(padx=20, pady=(20, 10), anchor="w")

        # Control Panel Card
        self.card = ctk.CTkFrame(self, fg_color="#18181b", corner_radius=10)
        self.card.pack(padx=20, pady=10, fill="x")
        self.card.grid_columnconfigure(1, weight=1)

        # Metadata Labels
        lbl_acc_t = ctk.CTkLabel(self.card, text="Account ID:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#a1a1aa")
        lbl_acc_t.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        lbl_acc_v = ctk.CTkLabel(self.card, text=self.account_id, font=ctk.CTkFont(size=14, weight="bold"), text_color="#ffffff")
        lbl_acc_v.grid(row=0, column=1, padx=10, pady=(15, 5), sticky="w")

        lbl_page_t = ctk.CTkLabel(self.card, text="Target Page:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#a1a1aa")
        lbl_page_t.grid(row=1, column=0, padx=20, pady=5, sticky="w")

        lbl_page_v = ctk.CTkLabel(self.card, text=self.target_page, font=ctk.CTkFont(size=14, weight="bold"), text_color="#3b82f6")
        lbl_page_v.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        lbl_prof_t = ctk.CTkLabel(self.card, text="Persistent Profile:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#a1a1aa")
        lbl_prof_t.grid(row=2, column=0, padx=20, pady=5, sticky="w")

        lbl_prof_v = ctk.CTkLabel(self.card, text=f"data/accounts/{self.account_id}/user_data/", font=ctk.CTkFont(family="Consolas", size=11), text_color="#71717a")
        lbl_prof_v.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        # Run Automation Button
        btn_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        btn_frame.grid(row=3, column=0, columnspan=2, padx=20, pady=(15, 20), sticky="w")

        self.btn_run = ctk.CTkButton(
            btn_frame,
            text="RUN AUTOMATION",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=40,
            command=self.on_run_automation_clicked
        )
        self.btn_run.pack(side="left")

    def on_run_automation_clicked(self):
        """Triggers automation workflow in background worker thread."""
        thread = threading.Thread(target=self._run_automation_worker, daemon=True)
        thread.start()

    def _run_automation_worker(self):
        log_info(f"[AUTOMATION] Initiating Milestone 3 Page Switch for Account '{self.account_id}' -> Page '{self.target_page}'...", tag="AUTOMATION")

        sm_engine = StateMachine(account_id=self.account_id, target_page=self.target_page)
        success = sm_engine.run_page_switch_workflow()

        if success:
            log_info("[AUTOMATION] Milestone 3 Page Switching & Active Page Identity Verification COMPLETED.", tag="AUTOMATION")
            log_info("[AUTOMATION] Browser remains visible on screen for manual verification.", tag="AUTOMATION")
        else:
            log_error("[AUTOMATION ERROR] Milestone 3 Page Switch workflow halted safely.", tag="AUTOMATION")
