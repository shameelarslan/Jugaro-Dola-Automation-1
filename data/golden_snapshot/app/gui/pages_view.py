import customtkinter as ctk

class PagesView(ctk.CTkFrame):
    """Pages management view (Milestone 1 GUI shell)."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        lbl = ctk.CTkLabel(
            self,
            text="Pages Management (Milestone 1 Shell)",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl.pack(padx=20, pady=20, anchor="w")

        info_box = ctk.CTkTextbox(self, height=120, fg_color="#1e1e1e")
        info_box.pack(padx=20, pady=10, fill="x")
        info_box.insert(
            "1.0",
            "Facebook Pages Association Shell.\n"
            "Associates accounts to target pages.\n"
            "Feature available in future page-management milestone."
        )
        info_box.configure(state="disabled")
