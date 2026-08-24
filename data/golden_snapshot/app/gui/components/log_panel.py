import customtkinter as ctk
from app.utils.logger import log_queue

class LogPanel(ctk.CTkFrame):
    """
    Live execution log panel widget.
    Reads from log_queue and streams formatted logs to UI without blocking main thread.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, corner_radius=10, fg_color="#1e1e1e", **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=15, pady=8, sticky="ew")

        lbl_header = ctk.CTkLabel(
            header_frame,
            text="LIVE EXECUTION LOGS",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#3b82f6"
        )
        lbl_header.pack(side="left")

        btn_clear = ctk.CTkButton(
            header_frame,
            text="Clear Logs",
            width=80,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color="#333333",
            hover_color="#444444",
            command=self.clear_logs
        )
        btn_clear.pack(side="right")

        # Scrollable Textbox
        self.textbox = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#121212",
            text_color="#e0e0e0",
            wrap="word",
            corner_radius=6
        )
        self.textbox.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")

    def append_log(self, level: str, message: str):
        """Appends log entry to text box."""
        prefix = ""
        if level == "ERROR":
            prefix = "[!] "
        elif level == "WARNING":
            prefix = "[?] "

        full_msg = f"{prefix}{message}\n"
        self.textbox.insert("end", full_msg)
        self.textbox.see("end")

    def clear_logs(self):
        self.textbox.delete("1.0", "end")
