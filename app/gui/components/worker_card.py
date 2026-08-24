"""
Active Worker Card Widget displaying live status, session, job, and timer.
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt

STATUS_COLOR_MAP = {
    "Idle": ("#64748b", "#1e293b"),
    "Starting": ("#3b82f6", "#1d4ed8"),
    "WAITING_FOR_NEW_MESSAGE": ("#f59e0b", "#78350f"),
    "WAITING_FOR_CONFIRMATION": ("#f59e0b", "#78350f"),
    "CONFIRMING_GENERATION": ("#06b6d4", "#155e75"),
    "GENERATING": ("#eab308", "#854d0e"),
    "WAITING_FOR_DOWNLOAD_BUTTON": ("#8b5cf6", "#4c1d95"),
    "REFRESHING": ("#a855f7", "#581c87"),
    "DOWNLOAD_TRIGGERED": ("#10b981", "#064e3b"),
    "VERIFYING_DOWNLOAD": ("#10b981", "#064e3b"),
    "Completed": ("#22c55e", "#14532d"),
    "Failed": ("#ef4444", "#7f1d1d"),
}

class WorkerCard(QFrame):
    def __init__(self, worker_id: int, parent=None):
        super().__init__(parent)
        self.worker_id = worker_id
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)
        
        # Header Row
        header_layout = QHBoxLayout()
        self.lbl_worker = QLabel(f"WORKER {self.worker_id:02d}")
        self.lbl_worker.setStyleSheet("color: #818cf8; font-weight: bold; font-size: 13px;")
        
        self.lbl_timer = QLabel("00:00")
        self.lbl_timer.setStyleSheet("color: #94a3b8; font-size: 12px; font-family: monospace;")
        
        header_layout.addWidget(self.lbl_worker)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_timer)
        
        # Status Badge Pill
        self.lbl_status = QLabel("IDLE")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("""
            QLabel {
                background-color: #334155;
                color: #cbd5e1;
                border-radius: 12px;
                padding: 4px 10px;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        
        # Info Details
        self.lbl_session = QLabel("Session: N/A")
        self.lbl_session.setStyleSheet("color: #94a3b8; font-size: 12px;")
        
        self.lbl_job = QLabel("Job: N/A")
        self.lbl_job.setStyleSheet("color: #cbd5e1; font-size: 12px; font-weight: 500;")
        
        self.lbl_prompt = QLabel("Prompt: Standby...")
        self.lbl_prompt.setStyleSheet("color: #64748b; font-size: 11px; font-style: italic;")
        self.lbl_prompt.setWordWrap(True)

        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.lbl_status)
        main_layout.addWidget(self.lbl_session)
        main_layout.addWidget(self.lbl_job)
        main_layout.addWidget(self.lbl_prompt)

    def update_state(self, state_dict: dict):
        stage = state_dict.get("stage", "Idle")
        elapsed = state_dict.get("elapsed_seconds", 0)
        mins, secs = divmod(elapsed, 60)
        self.lbl_timer.setText(f"{mins:02d}:{secs:02d}")
        
        # Update badge
        text_color, bg_color = STATUS_COLOR_MAP.get(stage, ("#ffffff", "#334155"))
        display_stage = stage.replace("_", " ").upper()
        self.lbl_status.setText(display_stage)
        self.lbl_status.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 12px;
                padding: 4px 10px;
                font-weight: bold;
                font-size: 11px;
            }}
        """)

        self.lbl_session.setText(f"Session: {state_dict.get('session_name', 'N/A')}")
        self.lbl_job.setText(f"Job: {state_dict.get('job_id', 'N/A')}")
        
        p_text = state_dict.get("prompt_text", "Standby...")
        if len(p_text) > 60:
            p_text = p_text[:60] + "..."
        self.lbl_prompt.setText(f"Prompt: {p_text}")
