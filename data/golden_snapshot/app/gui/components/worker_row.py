"""
Active Worker List Row Widget displaying compact live status, session, job, and timer.
Designed to fit cleanly on screen without scrolling.
"""

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt

STATUS_COLOR_MAP = {
    "Idle": ("#a1a1aa", "#3f3f46"),
    "Starting": ("#ffffff", "#2563eb"),
    "WAITING_FOR_NEW_MESSAGE": ("#ffffff", "#d97706"),
    "WAITING_FOR_CONFIRMATION": ("#ffffff", "#d97706"),
    "CONFIRMING_GENERATION": ("#ffffff", "#0284c7"),
    "GENERATING": ("#ffffff", "#ca8a04"),
    "WAITING_FOR_DOWNLOAD_BUTTON": ("#ffffff", "#7c3aed"),
    "REFRESHING": ("#ffffff", "#c084fc"),
    "DOWNLOAD_TRIGGERED": ("#ffffff", "#16a34a"),
    "VERIFYING_DOWNLOAD": ("#ffffff", "#16a34a"),
    "Completed": ("#ffffff", "#16a34a"),
    "Failed": ("#ffffff", "#dc2626"),
}

class WorkerRow(QFrame):
    def __init__(self, worker_id: int, parent=None):
        super().__init__(parent)
        self.worker_id = worker_id
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedHeight(36)
        self.setStyleSheet("""
            QFrame {
                background-color: #27272a;
                border: 1px solid #3f3f46;
                border-radius: 4px;
            }
            QFrame:hover {
                border: 1px solid #52525b;
            }
        """)
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 2, 10, 2)
        main_layout.setSpacing(10)
        
        # Worker ID Label
        self.lbl_worker = QLabel(f"⚡ WORKER {self.worker_id:02d}")
        self.lbl_worker.setFixedWidth(100)
        self.lbl_worker.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 12px;")
        
        # Status Badge Pill
        self.lbl_status = QLabel("IDLE")
        self.lbl_status.setFixedWidth(145)
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("""
            QLabel {
                background-color: #3f3f46;
                color: #a1a1aa;
                border-radius: 8px;
                padding: 2px 6px;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        
        # Session Name
        self.lbl_session = QLabel("Session: N/A")
        self.lbl_session.setFixedWidth(115)
        self.lbl_session.setStyleSheet("color: #e4e4e7; font-size: 12px;")
        
        # Job ID
        self.lbl_job = QLabel("Job: N/A")
        self.lbl_job.setFixedWidth(125)
        self.lbl_job.setStyleSheet("color: #e4e4e7; font-size: 12px; font-weight: 500;")
        
        # Prompt Text
        self.lbl_prompt = QLabel("Prompt: Standby...")
        self.lbl_prompt.setStyleSheet("color: #a1a1aa; font-size: 11px; font-style: italic;")
        
        # Timer
        self.lbl_timer = QLabel("00:00")
        self.lbl_timer.setFixedWidth(55)
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_timer.setStyleSheet("color: #38bdf8; font-size: 12px; font-family: monospace; font-weight: bold;")

        main_layout.addWidget(self.lbl_worker)
        main_layout.addWidget(self.lbl_status)
        main_layout.addWidget(self.lbl_session)
        main_layout.addWidget(self.lbl_job)
        main_layout.addWidget(self.lbl_prompt, 1) # Expandable prompt field
        main_layout.addWidget(self.lbl_timer)

    def update_state(self, state_dict: dict):
        stage = state_dict.get("stage", "Idle")
        elapsed = state_dict.get("elapsed_seconds", 0)
        mins, secs = divmod(elapsed, 60)
        self.lbl_timer.setText(f"{mins:02d}:{secs:02d}")
        
        # Update badge
        text_color, bg_color = STATUS_COLOR_MAP.get(stage, ("#ffffff", "#3f3f46"))
        display_stage = stage.replace("_", " ").upper()
        self.lbl_status.setText(display_stage)
        self.lbl_status.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 8px;
                padding: 2px 6px;
                font-weight: bold;
                font-size: 11px;
            }}
        """)

        self.lbl_session.setText(f"Session: {state_dict.get('session_name', 'N/A')}")
        self.lbl_job.setText(f"Job: {state_dict.get('job_id', 'N/A')}")
        
        p_text = state_dict.get("prompt_text", "Standby...")
        if len(p_text) > 85:
            p_text = p_text[:85] + "..."
        self.lbl_prompt.setText(f"Prompt: {p_text}")
