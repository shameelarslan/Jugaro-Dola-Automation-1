"""
Interactive Onboarding Tutorial & Feature Walkthrough Dialogs.
Provides a clean, fixed-position welcome prompt and step-by-step guided feature tour
with automatic tab navigation and clear English explanations.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QWidget, QProgressBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from app.core.database import db

class WelcomeTutorialPromptDialog(QDialog):
    """
    First-time welcome modal asking the user if they want a guided tour
    or if they want to skip as an expert. (Fixed position, non-draggable).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to Waqas's Automation Pro")
        self.setFixedSize(540, 360)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0f19;
                border: 1.5px solid #334155;
                border-radius: 12px;
            }
        """)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(14)

        # Header Bar with Close Button
        hdr_frame = QFrame()
        hdr_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e1b4b, stop:1 #0f172a);
                border: 1px solid #3730a3;
                border-radius: 10px;
                padding: 10px 14px;
            }
        """)
        hdr_layout = QHBoxLayout(hdr_frame)
        hdr_layout.setContentsMargins(6, 2, 6, 2)
        hdr_layout.setSpacing(12)

        icon_lbl = QLabel("🚀")
        icon_lbl.setStyleSheet("font-size: 28px;")
        hdr_layout.addWidget(icon_lbl)

        v_title = QVBoxLayout()
        v_title.setSpacing(2)
        lbl_title = QLabel("5-Step Guided Feature Tour")
        lbl_title.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 800;")
        lbl_sub = QLabel("Commercial Multi-Session AI Video Automation Suite")
        lbl_sub.setStyleSheet("color: #94a3b8; font-size: 11px;")
        v_title.addWidget(lbl_title)
        v_title.addWidget(lbl_sub)
        hdr_layout.addLayout(v_title)
        hdr_layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setFixedSize(28, 28)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #94a3b8;
                font-size: 13px;
                font-weight: bold;
                border: 1px solid #334155;
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: #ffffff;
                border-color: #ef4444;
            }
        """)
        btn_close.clicked.connect(self._on_skip)
        hdr_layout.addWidget(btn_close)

        layout.addWidget(hdr_frame)

        # Body Message Card
        msg_card = QFrame()
        msg_card.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1f2937;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        msg_layout = QVBoxLayout(msg_card)
        msg_layout.setSpacing(8)

        lbl_question = QLabel("Would you like a quick 1-minute guided tour to explore how to generate videos in bulk and use all features?")
        lbl_question.setWordWrap(True)
        lbl_question.setStyleSheet("color: #e2e8f0; font-size: 12.5px; font-weight: 500; line-height: 1.4;")
        msg_layout.addWidget(lbl_question)

        # Bullet points
        bullets = [
            "✨  Rolling Multi-Session concurrency for maximum generation speed",
            "📝  500+ Bulk Prompts library with instant zero-lag import",
            "📥  Automated watermark removal & direct MP4 video downloads"
        ]
        for b in bullets:
            bl = QLabel(b)
            bl.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 600;")
            msg_layout.addWidget(bl)

        layout.addWidget(msg_card)
        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        btn_skip = QPushButton("⚡  No, I'm an Expert")
        btn_skip.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_skip.setFixedHeight(38)
        btn_skip.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #94a3b8;
                font-size: 12px;
                font-weight: 600;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #ffffff;
            }
        """)
        btn_skip.clicked.connect(self._on_skip)

        btn_tour = QPushButton("📖  Learn How to Use (Start Tour)")
        btn_tour.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_tour.setFixedHeight(38)
        btn_tour.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #7c3aed);
                color: #ffffff;
                font-size: 12px;
                font-weight: 800;
                border: none;
                border-radius: 8px;
                padding: 0 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #6d28d9);
            }
        """)
        btn_tour.clicked.connect(self._on_start_tour)

        btn_layout.addWidget(btn_skip)
        btn_layout.addWidget(btn_tour)
        layout.addLayout(btn_layout)

    def _on_skip(self):
        # Mark tutorial completed in config
        cfg = db.load_app_config()
        cfg.tutorial_completed = True
        db.save_app_config(cfg)
        self.done(0)

    def _on_start_tour(self):
        self.done(1)


class InteractiveTourDialog(QDialog):
    """
    Step-by-step guided tour dialog that navigates through the software tabs
    and explains each key workflow section in English. (Fixed position, non-draggable).
    """
    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self.current_step = 0

        self.setWindowTitle("Interactive Software Tour — Step 1 of 5")
        self.setFixedSize(580, 420)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0f19;
                border: 1.5px solid #334155;
                border-radius: 12px;
            }
        """)

        self.steps_data = [
            {
                "tab_idx": 0,
                "badge": "STEP 1 OF 5",
                "icon": "📊",
                "title": "Executive Dashboard & Telemetry",
                "desc": "The Dashboard gives you live real-time statistics and overview counters.",
                "points": [
                    "• View total pending, running, completed, and failed prompt counters.",
                    "• See active parallel session slots and live worker stage progression.",
                    "• Real-time log monitor at the bottom streams background execution activity."
                ]
            },
            {
                "tab_idx": 1,
                "badge": "STEP 2 OF 5",
                "icon": "🔑",
                "title": "Sessions & Account Profiles",
                "desc": "Manage your Dola and Google browser accounts here.",
                "points": [
                    "• Click '+ Add Session' to manually paste cookies or log in via browser.",
                    "• Click '📥 Import JSON' to load multiple cookie profiles in bulk.",
                    "• Sessions with expired daily quotas automatically enter a 24-hour safe cooldown."
                ]
            },
            {
                "tab_idx": 2,
                "badge": "STEP 3 OF 5",
                "icon": "📝",
                "title": "Prompts Library (500+ Capacity)",
                "desc": "Add and organize all your video prompts in bulk without UI freezing.",
                "points": [
                    "• Click '📋 Paste Prompts' to paste dozens or hundreds of lines at once.",
                    "• Click '📂 Import File' to upload prompt lists directly from .txt files.",
                    "• Use '🧹 Clear Completed' anytime to delete finished prompts from the library."
                ]
            },
            {
                "tab_idx": 3,
                "badge": "STEP 4 OF 5",
                "icon": "⚡",
                "title": "Automation Center & Rolling Pool",
                "desc": "Configure your execution settings and start the automation engine.",
                "points": [
                    "• Set 'Sessions At A Time' to control how many browsers run simultaneously.",
                    "• Set 'Videos Per Session' to distribute prompts evenly across sessions.",
                    "• Click '📁 Browse...' under 'Save Output To' to choose your custom video folder.",
                    "• Click '▶ START AUTOMATION' and select your active sessions to launch!"
                ]
            },
            {
                "tab_idx": 4,
                "badge": "STEP 5 OF 5",
                "icon": "📥",
                "title": "Downloads & Video Player",
                "desc": "Access and preview all downloaded, watermark-free MP4 videos.",
                "points": [
                    "• All generated videos are verified and saved into your selected directory.",
                    "• Built-in AI watermark remover automatically blurs watermarks cleanly.",
                    "• Click '▶ Play' on any row to preview the video in your default media player."
                ]
            }
        ]

        self._init_ui()
        self._show_step(0)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(22, 18, 22, 18)
        main_layout.setSpacing(12)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(self.steps_data))
        self.progress_bar.setValue(1)
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e293b;
                border-radius: 2px;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #8b5cf6);
                border-radius: 2px;
            }
        """)
        main_layout.addWidget(self.progress_bar)

        # Header Frame
        hdr_frame = QFrame()
        hdr_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #141829, stop:1 #1c213d);
                border: 1px solid rgba(124, 77, 255, 0.3);
                border-radius: 10px;
                padding: 8px 12px;
            }
        """)
        hdr_layout = QHBoxLayout(hdr_frame)
        hdr_layout.setContentsMargins(4, 2, 4, 2)
        hdr_layout.setSpacing(12)

        self.lbl_icon = QLabel("📊")
        self.lbl_icon.setStyleSheet("font-size: 26px;")
        hdr_layout.addWidget(self.lbl_icon)

        v_hdr = QVBoxLayout()
        v_hdr.setSpacing(2)

        self.lbl_badge = QLabel("STEP 1 OF 5")
        self.lbl_badge.setStyleSheet("""
            color: #c084fc;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1px;
        """)
        self.lbl_title = QLabel("Executive Dashboard & Telemetry")
        self.lbl_title.setStyleSheet("color: #ffffff; font-size: 14.5px; font-weight: 800;")

        v_hdr.addWidget(self.lbl_badge)
        v_hdr.addWidget(self.lbl_title)
        hdr_layout.addLayout(v_hdr)
        hdr_layout.addStretch()

        btn_top_close = QPushButton("✕")
        btn_top_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_top_close.setFixedSize(26, 26)
        btn_top_close.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #94a3b8;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid #334155;
                border-radius: 13px;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: #ffffff;
                border-color: #ef4444;
            }
        """)
        btn_top_close.clicked.connect(self._finish_and_close)
        hdr_layout.addWidget(btn_top_close)

        main_layout.addWidget(hdr_frame)

        # Content Card
        self.content_card = QFrame()
        self.content_card.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1f2937;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        self.content_layout = QVBoxLayout(self.content_card)
        self.content_layout.setSpacing(8)

        self.lbl_desc = QLabel()
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 500;")
        self.content_layout.addWidget(self.lbl_desc)

        self.lbl_p1 = QLabel()
        self.lbl_p1.setWordWrap(True)
        self.lbl_p1.setStyleSheet("color: #e2e8f0; font-size: 11.5px;")
        self.lbl_p2 = QLabel()
        self.lbl_p2.setWordWrap(True)
        self.lbl_p2.setStyleSheet("color: #e2e8f0; font-size: 11.5px;")
        self.lbl_p3 = QLabel()
        self.lbl_p3.setWordWrap(True)
        self.lbl_p3.setStyleSheet("color: #e2e8f0; font-size: 11.5px;")

        self.content_layout.addWidget(self.lbl_p1)
        self.content_layout.addWidget(self.lbl_p2)
        self.content_layout.addWidget(self.lbl_p3)

        main_layout.addWidget(self.content_card)
        main_layout.addStretch()

        # Bottom Navigation Controls
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        self.btn_skip = QPushButton("Skip Tour ✕")
        self.btn_skip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_skip.setFixedHeight(34)
        self.btn_skip.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #64748b;
                font-size: 11px;
                font-weight: 600;
                border: none;
                padding: 0 10px;
            }
            QPushButton:hover {
                color: #ef4444;
            }
        """)
        self.btn_skip.clicked.connect(self._finish_and_close)

        self.btn_prev = QPushButton("◀  Previous")
        self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev.setFixedHeight(34)
        self.btn_prev.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #cbd5e1;
                font-size: 11.5px;
                font-weight: 600;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #ffffff;
            }
            QPushButton:disabled {
                background-color: #0f172a;
                color: #475569;
                border-color: #1e293b;
            }
        """)
        self.btn_prev.clicked.connect(self._on_prev)

        self.btn_next = QPushButton("Next Step ➜")
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.setFixedHeight(34)
        self.btn_next.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #7c3aed);
                color: #ffffff;
                font-size: 11.5px;
                font-weight: 800;
                border: none;
                border-radius: 6px;
                padding: 0 18px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #6d28d9);
            }
        """)
        self.btn_next.clicked.connect(self._on_next)

        btn_bar.addWidget(self.btn_skip)
        btn_bar.addStretch()
        btn_bar.addWidget(self.btn_prev)
        btn_bar.addWidget(self.btn_next)
        main_layout.addLayout(btn_bar)

    def _show_step(self, step_idx: int):
        self.current_step = step_idx
        data = self.steps_data[step_idx]

        self.progress_bar.setValue(step_idx + 1)
        self.setWindowTitle(f"Guided Tour — {data['badge']}")
        self.lbl_badge.setText(f"Interactive Tour | {data['badge']}")
        self.lbl_icon.setText(data["icon"])
        self.lbl_title.setText(data["title"])
        self.lbl_desc.setText(data["desc"])

        pts = data["points"]
        self.lbl_p1.setText(pts[0] if len(pts) > 0 else "")
        self.lbl_p2.setText(pts[1] if len(pts) > 1 else "")
        self.lbl_p3.setText(pts[2] if len(pts) > 2 else "")

        self.btn_prev.setEnabled(step_idx > 0)
        if step_idx == len(self.steps_data) - 1:
            self.btn_next.setText("Finish Tour 🎉")
            self.btn_next.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10b981);
                    color: #ffffff;
                    font-size: 11.5px;
                    font-weight: 800;
                    border: none;
                    border-radius: 6px;
                    padding: 0 20px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #047857, stop:1 #059669);
                }
            """)
        else:
            self.btn_next.setText("Next Step ➜")
            self.btn_next.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #7c3aed);
                    color: #ffffff;
                    font-size: 11.5px;
                    font-weight: 800;
                    border: none;
                    border-radius: 6px;
                    padding: 0 18px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #6d28d9);
                }
            """)

        # Automatically switch MainWindow sidebar to this step's tab
        try:
            if hasattr(self.main_window, "sidebar"):
                self.main_window.sidebar.setCurrentRow(data["tab_idx"])
        except Exception:
            pass

    def _on_prev(self):
        if self.current_step > 0:
            self._show_step(self.current_step - 1)

    def _on_next(self):
        if self.current_step < len(self.steps_data) - 1:
            self._show_step(self.current_step + 1)
        else:
            self._finish_and_close()

    def _finish_and_close(self):
        # Save completed status to DB
        cfg = db.load_app_config()
        cfg.tutorial_completed = True
        db.save_app_config(cfg)
        self.accept()
