import customtkinter as ctk

class SchedulerView(ctk.CTkFrame):
    """Scheduler View (Milestone 1 Shell)."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        lbl = ctk.CTkLabel(
            self,
            text="Scheduler (Milestone 1 Shell)",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl.pack(padx=20, pady=20, anchor="w")
