"""
Contact Us Dialog - Modern Social Connect Window (Facebook & WhatsApp Direct Links).
"""

import webbrowser
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

FACEBOOK_URL = "https://www.facebook.com/wqas.shwkt/"
WHATSAPP_URL = "https://wa.me/923157664936?text=Hey!%20I%20need%20some%20extra%20information%20about%20your%20products."

class ContactDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Contact Us - Waqas Automation")
        self.setFixedSize(480, 430)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        card = QFrame()
        card.setObjectName("ContactCard")
        card.setStyleSheet("""
            QFrame#ContactCard {
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

        # Header
        hdr_layout = QHBoxLayout()
        hdr_vbox = QVBoxLayout()
        hdr_vbox.setSpacing(2)
        lbl_title = QLabel("💬 Direct Support & Community")
        lbl_title.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: 800;")
        lbl_sub = QLabel("Connect directly with Waqas Shaukat for queries & feedback")
        lbl_sub.setStyleSheet("color: #8f9bb3; font-size: 12px;")
        hdr_vbox.addWidget(lbl_title)
        hdr_vbox.addWidget(lbl_sub)
        hdr_layout.addLayout(hdr_vbox)

        hdr_layout.addStretch()

        btn_x = QPushButton("✕")
        btn_x.setFixedSize(32, 32)
        btn_x.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_x.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #94a3b8;
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

        # ── 1. WhatsApp Button ──────────────────────────────────────────────
        btn_wa = QPushButton("💬   Chat on WhatsApp (Direct Support)")
        btn_wa.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_wa.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #123320, stop:1 #1e4d30);
                color: #25D366;
                border: 1.5px solid #25D366;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 800;
                padding: 15px;
                text-align: center;
            }
            QPushButton:hover {
                background: #25D366;
                color: #000000;
            }
        """)
        btn_wa.clicked.connect(lambda: webbrowser.open(WHATSAPP_URL))
        card_layout.addWidget(btn_wa)

        # ── 2. Facebook Button ──────────────────────────────────────────────
        btn_fb = QPushButton("📘   Visit Facebook Profile (Waqas Shaukat)")
        btn_fb.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_fb.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #102347, stop:1 #1a3870);
                color: #38bdf8;
                border: 1.5px solid #1877F2;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 800;
                padding: 15px;
                text-align: center;
            }
            QPushButton:hover {
                background: #1877F2;
                color: #ffffff;
            }
        """)
        btn_fb.clicked.connect(lambda: webbrowser.open(FACEBOOK_URL))
        card_layout.addWidget(btn_fb)

        card_layout.addStretch()

        # Footer
        lbl_ft = QLabel("🌐 Clicking an option will open your default browser.")
        lbl_ft.setStyleSheet("color: #64748b; font-size: 11px; font-style: italic;")
        lbl_ft.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(lbl_ft)

        main_layout.addWidget(card)
