"""
User Profile Details Dialog - Displays active user information, license tier, and logout.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from app.core.cloud_manager import cloud_manager

class UserProfileDialog(QDialog):
    sign_out_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Account & License Details")
        self.setFixedSize(460, 490)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        card = QFrame()
        card.setObjectName("ProfileCard")
        card.setStyleSheet("""
            QFrame#ProfileCard {
                background-color: #111422;
                border: 1px solid rgba(124, 77, 255, 0.5);
                border-radius: 16px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(35)
        shadow.setColor(QColor(124, 77, 255, 110))
        shadow.setOffset(0, 8)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(26, 26, 26, 24)
        card_layout.setSpacing(16)

        user = cloud_manager.current_user or {}
        email = user.get("email", "guest@waqasautomation.com")
        full_name = user.get("full_name") or email.split("@")[0].capitalize()
        status = user.get("status", "Active")
        initials = (full_name[:2]).upper() if len(full_name) >= 2 else "WA"

        # Top Header (Avatar + Name + Close)
        hdr_layout = QHBoxLayout()
        avatar_lbl = QLabel(initials)
        avatar_lbl.setFixedSize(54, 54)
        avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_lbl.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7c4dff, stop:1 #3b82f6);
            color: #ffffff;
            font-size: 20px;
            font-weight: 900;
            border-radius: 27px;
            border: 2px solid rgba(255, 255, 255, 0.3);
        """)
        hdr_layout.addWidget(avatar_lbl)

        hdr_vbox = QVBoxLayout()
        hdr_vbox.setSpacing(2)
        lbl_name = QLabel(full_name)
        lbl_name.setStyleSheet("color: #ffffff; font-size: 19px; font-weight: 900;")
        lbl_email = QLabel(email)
        lbl_email.setStyleSheet("color: #8f9bb3; font-size: 12px;")
        hdr_vbox.addWidget(lbl_name)
        hdr_vbox.addWidget(lbl_email)
        hdr_layout.addLayout(hdr_vbox)

        hdr_layout.addStretch()

        btn_x = QPushButton("✕")
        btn_x.setFixedSize(32, 32)
        btn_x.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_x.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #8f9bb3;
                font-size: 14px;
                font-weight: bold;
                border-radius: 16px;
                border: none;
            }
            QPushButton:hover {
                background: #ef4444;
                color: #ffffff;
            }
        """)
        btn_x.clicked.connect(self.accept)
        hdr_layout.addWidget(btn_x)

        card_layout.addLayout(hdr_layout)

        # Divider
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.1);")
        card_layout.addWidget(divider)

        # Info Rows Container
        info_box = QVBoxLayout()
        info_box.setSpacing(12)

        info_box.addLayout(self._create_info_row("License Tier:", "🟢 Free Lifetime License Active", "#10b981"))
        info_box.addLayout(self._create_info_row("Account Status:", f"● {status}", "#00e676" if status == "Active" else "#ff9100"))
        
        is_master = email.lower() in ("waqasshoukat2193@gmail.com", "ali@gmail.com")
        role_str = "👑 Master Admin & Developer" if is_master else "👤 Verified SaaS Creator"
        info_box.addLayout(self._create_info_row("Role:", role_str, "#9d7aff" if is_master else "#38bdf8"))

        card_layout.addLayout(info_box)

        card_layout.addStretch()

        # Action Buttons (Sign Out / Close)
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        btn_logout = QPushButton("🚪 Sign Out")
        btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_logout.setStyleSheet("""
            QPushButton {
                background-color: #2a151d;
                color: #ff5252;
                border: 1px solid #ff5252;
                border-radius: 8px;
                font-weight: 800;
                font-size: 13px;
                padding: 11px;
            }
            QPushButton:hover {
                background-color: #ff5252;
                color: #ffffff;
            }
        """)
        btn_logout.clicked.connect(self._handle_logout)
        btn_box.addWidget(btn_logout)

        btn_close = QPushButton("Close")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #1a1d2e;
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                font-weight: 800;
                font-size: 13px;
                padding: 11px;
            }
            QPushButton:hover {
                background-color: #242942;
            }
        """)
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)

        card_layout.addLayout(btn_box)

        main_layout.addWidget(card)

    def _create_info_row(self, label: str, value: str, val_color: str):
        row = QHBoxLayout()
        lbl_k = QLabel(label)
        lbl_k.setStyleSheet("color: #8f9bb3; font-size: 13px; font-weight: 600;")
        lbl_v = QLabel(value)
        lbl_v.setStyleSheet(f"color: {val_color}; font-size: 13px; font-weight: 800;")
        row.addWidget(lbl_k)
        row.addStretch()
        row.addWidget(lbl_v)
        return row

    def _handle_logout(self):
        self.accept()
        self.sign_out_requested.emit()
