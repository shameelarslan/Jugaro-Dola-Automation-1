import customtkinter as ctk

class SeedingView(ctk.CTkFrame):
    """Seeding View (Milestone 1 Shell)."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        lbl = ctk.CTkLabel(
            self,
            text="Seeding Module (Milestone 1 Shell)",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl.pack(padx=20, pady=20, anchor="w")
