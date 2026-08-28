"""
Modern Cloud Update Dialog for Waqas Automation Pro.
Displays new release info, changelog highlights, and a download progress bar.
"""

import sys
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from app.core.updater import updater

class UpdateDownloadWorker(QThread):
    progress_changed = pyqtSignal(int)
    finished = pyqtSignal(bool)

    def __init__(self, download_url: str):
        super().__init__()
        self.download_url = download_url

    def run(self):
        def _cb(p):
            self.progress_changed.emit(p)
        ok = updater.download_and_install_update(self.download_url, progress_callback=_cb)
        self.finished.emit(ok)

class UpdateDialog(QDialog):
    def __init__(self, release_info: dict, parent=None):
        super().__init__(parent)
        self.release_info = release_info
        self.worker_thread = None

        self.setWindowTitle("Software Update Available")
        self.setFixedSize(500, 420)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)

        card = QFrame()
        card.setObjectName("UpdateCard")
        card.setStyleSheet("""
            QFrame#UpdateCard {
                background-color: #111424;
                border: 1px solid rgba(124, 77, 255, 0.5);
                border-radius: 16px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(124, 77, 255, 100))
        shadow.setOffset(0, 6)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 22, 24, 22)
        card_layout.setSpacing(14)

        # Header: Icon + Title + Version
        hdr = QHBoxLayout()
        icon_lbl = QLabel("🚀")
        icon_lbl.setFixedSize(42, 42)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7c4dff, stop:1 #3b82f6);
            font-size: 20px;
            border-radius: 21px;
        """)
        hdr.addWidget(icon_lbl)

        hdr_v = QVBoxLayout()
        hdr_v.setSpacing(2)
        lbl_t = QLabel("New Update Available!")
        lbl_t.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: 900;")
        
        ver_str = self.release_info.get("version", "Latest")
        lbl_v = QLabel(f"Version {ver_str} is ready to install")
        lbl_v.setStyleSheet("color: #34d399; font-size: 12px; font-weight: 700;")
        hdr_v.addWidget(lbl_t)
        hdr_v.addWidget(lbl_v)
        hdr.addLayout(hdr_v)

        hdr.addStretch()
        card_layout.addLayout(hdr)

        # Changelog Box
        lbl_cl = QLabel("What's New in this update:")
        lbl_cl.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 700;")
        card_layout.addWidget(lbl_cl)

        self.txt_changelog = QTextEdit()
        self.txt_changelog.setReadOnly(True)
        changelog_text = self.release_info.get("changelog") or "• Performance optimizations and stability improvements.\n• Updated Dola AI automation engine."
        self.txt_changelog.setPlainText(changelog_text)
        self.txt_changelog.setStyleSheet("""
            QTextEdit {
                background-color: #0d101d;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                color: #e2e8f0;
                font-size: 12px;
                padding: 10px;
            }
        """)
        card_layout.addWidget(self.txt_changelog)

        # Progress Bar (Hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e293b;
                border-radius: 6px;
                border: none;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c4dff, stop:1 #10b981);
                border-radius: 6px;
            }
        """)
        card_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("")
        self.lbl_status.setVisible(False)
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 700;")
        card_layout.addWidget(self.lbl_status)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        is_mandatory = self.release_info.get("is_mandatory", False)

        if not is_mandatory:
            self.btn_later = QPushButton("Later")
            self.btn_later.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_later.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.08);
                    color: #94a3b8;
                    font-size: 12px;
                    font-weight: 700;
                    border: none;
                    border-radius: 8px;
                    padding: 10px 18px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.15);
                    color: #ffffff;
                }
            """)
            self.btn_later.clicked.connect(self.reject)
            btn_layout.addWidget(self.btn_later)

        btn_layout.addStretch()

        self.btn_update = QPushButton("🚀  Update Now")
        self.btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_update.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
                color: #ffffff;
                font-size: 13px;
                font-weight: 800;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #10b981);
            }
        """)
        self.btn_update.clicked.connect(self._start_download)
        btn_layout.addWidget(self.btn_update)

        card_layout.addLayout(btn_layout)
        main_layout.addWidget(card)

    def _start_download(self):
        download_url = self.release_info.get("download_url")
        if not download_url:
            # If no direct patch URL, inform user
            self.lbl_status.setText("✅ You are on the latest build! No download required.")
            self.lbl_status.setVisible(True)
            return

        self.btn_update.setEnabled(False)
        if hasattr(self, "btn_later"):
            self.btn_later.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.lbl_status.setVisible(True)
        self.lbl_status.setText("Downloading update patch...")

        self.worker_thread = UpdateDownloadWorker(download_url)
        self.worker_thread.progress_changed.connect(self.progress_bar.setValue)
        self.worker_thread.finished.connect(self._on_download_finished)
        self.worker_thread.start()

    def _on_download_finished(self, success: bool):
        if success:
            self.lbl_status.setText("✅ Update installed! Restarting application...")
            self.lbl_status.setStyleSheet("color: #10b981; font-size: 12px; font-weight: bold;")
            # Launch fresh instance and quit current
            main_script = Path(__file__).resolve().parent.parent.parent / "main.py"
            subprocess.Popen([sys.executable, str(main_script)])
            sys.exit(0)
        else:
            self.lbl_status.setText("❌ Download failed. Please try again later.")
            self.lbl_status.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: bold;")
            self.btn_update.setEnabled(True)
            if hasattr(self, "btn_later"):
                self.btn_later.setEnabled(True)
