import customtkinter as ctk
import config
from app.utils.logger import log_info

class SettingsView(ctk.CTkFrame):
    """
    Settings View.
    Configures Debug Mode (ON/OFF), Headless toggle, and physical browser window dimensions.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        lbl_title = ctk.CTkLabel(
            self,
            text="Browser & System Settings",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_title.pack(padx=20, pady=(20, 10), anchor="w")

        # Container Frame
        form = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=10)
        form.pack(padx=20, pady=10, fill="x")

        # Debug Mode Switch
        self.sw_debug = ctk.CTkSwitch(
            form,
            text="Debug Mode (Visible Window + Slow Motion)",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.on_debug_toggle
        )
        self.sw_debug.pack(padx=20, pady=(20, 10), anchor="w")
        if config.DEFAULT_DEBUG_MODE:
            self.sw_debug.select()

        # Physical Window Dimensions
        dim_frame = ctk.CTkFrame(form, fg_color="transparent")
        dim_frame.pack(padx=20, pady=10, fill="x")

        lbl_width = ctk.CTkLabel(dim_frame, text="Browser Window Width (px):")
        lbl_width.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")
        self.entry_width = ctk.CTkEntry(dim_frame, width=100)
        self.entry_width.insert(0, str(config.DEFAULT_WINDOW_WIDTH))
        self.entry_width.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        lbl_height = ctk.CTkLabel(dim_frame, text="Browser Window Height (px):")
        lbl_height.grid(row=1, column=0, padx=(0, 10), pady=5, sticky="w")
        self.entry_height = ctk.CTkEntry(dim_frame, width=100)
        self.entry_height.insert(0, str(config.DEFAULT_WINDOW_HEIGHT))
        self.entry_height.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        lbl_slowmo = ctk.CTkLabel(dim_frame, text="Slow Motion Delay (ms):")
        lbl_slowmo.grid(row=2, column=0, padx=(0, 10), pady=5, sticky="w")
        self.entry_slowmo = ctk.CTkEntry(dim_frame, width=100)
        self.entry_slowmo.insert(0, str(config.DEFAULT_SLOW_MO))
        self.entry_slowmo.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        btn_save = ctk.CTkButton(
            form,
            text="Save Settings",
            fg_color="#10b981",
            hover_color="#059669",
            command=self.save_settings
        )
        btn_save.pack(padx=20, pady=(10, 20), anchor="w")

    def on_debug_toggle(self):
        is_debug = bool(self.sw_debug.get())
        log_info(f"Debug Mode set to: {'ON' if is_debug else 'OFF'}", tag="SETTINGS")

    def save_settings(self):
        try:
            config.DEFAULT_DEBUG_MODE = bool(self.sw_debug.get())
            config.DEFAULT_WINDOW_WIDTH = int(self.entry_width.get())
            config.DEFAULT_WINDOW_HEIGHT = int(self.entry_height.get())
            config.DEFAULT_SLOW_MO = int(self.entry_slowmo.get())
            log_info("Settings saved successfully.", tag="SETTINGS")
        except ValueError:
            log_info("Error: Invalid numeric value for window size/delay.", tag="ERROR")
