import customtkinter as ctk
from app.storage.file_manager import FileManager

class ContentView(ctk.CTkFrame):
    """Content & Video Library View."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.file_manager = FileManager()

        lbl = ctk.CTkLabel(
            self,
            text="Content & Media Library",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl.pack(padx=20, pady=20, anchor="w")

        info_box = ctk.CTkTextbox(self, height=120, fg_color="#1e1e1e")
        info_box.pack(padx=20, pady=10, fill="x")
        info_box.insert(
            "1.0",
            "Video Directories:\n"
            "- Pending Input: data/input/{PageName}/\n"
            "- Verified Archive: data/archive/{PageName}/\n\n"
            "Videos move to archive ONLY after publication verification."
        )
        info_box.configure(state="disabled")
