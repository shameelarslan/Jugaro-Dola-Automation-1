"""
About Developer & Creator Dialog - Professional About Window.
"""

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Developer & Project")
        self.setFixedSize(540, 580)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        card = QFrame()
        card.setObjectName("AboutCard")
        card.setStyleSheet("""
            QFrame#AboutCard {
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
        card_layout.setSpacing(14)

        # Header (Avatar + Title + Close)
        hdr_layout = QHBoxLayout()
        
        avatar_lbl = QLabel("WS")
        avatar_lbl.setFixedSize(50, 50)
        avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_lbl.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7c4dff, stop:1 #3b82f6);
            color: #ffffff;
            font-size: 19px;
            font-weight: 900;
            border-radius: 25px;
            border: 2px solid rgba(255, 255, 255, 0.3);
        """)
        hdr_layout.addWidget(avatar_lbl)

        hdr_vbox = QVBoxLayout()
        hdr_vbox.setSpacing(2)
        lbl_name = QLabel("Waqas Shaukat")
        lbl_name.setStyleSheet("color: #ffffff; font-size: 19px; font-weight: 900;")
        lbl_role = QLabel("Developer & Creator • Waqas Automation Pro")
        lbl_role.setStyleSheet("color: #9d7aff; font-size: 12px; font-weight: 700;")
        hdr_vbox.addWidget(lbl_name)
        hdr_vbox.addWidget(lbl_role)
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

        # Message Scroll Box
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(4, 4, 4, 4)
        content_layout.setSpacing(12)

        about_text = (
            "Hello! My name is Waqas Shaukat, and I am the developer of this tool.\n\n"
            "I created this project with a simple goal: to make AI and video automation more accessible, useful, and easy to understand.\n\n"
            "My aim is not only to build useful software, but also to share knowledge, help others learn, and spread free knowledge about AI and automation.\n\n"
            "I hope this tool helps you save time, explore new possibilities, and turn your creative ideas into reality more easily.\n\n"
            "This project is a small contribution toward making technology and knowledge more accessible to everyone.\n\n"
            "Thank you for using the tool and being part of this journey. ❤️\n\n"
            "— Waqas Shaukat\nDeveloper & Creator"
        )

        lbl_body = QLabel(about_text)
        lbl_body.setStyleSheet("""
            color: #e2e8f0;
            font-size: 13px;
            line-height: 1.6;
            font-family: 'Segoe UI', Inter, sans-serif;
        """)
        lbl_body.setWordWrap(True)
        content_layout.addWidget(lbl_body)

        scroll.setWidget(content_widget)
        card_layout.addWidget(scroll)

        # Footer Button
        btn_close = QPushButton("Close")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c4dff, stop:1 #651fff);
                color: #ffffff;
                font-size: 13px;
                font-weight: 800;
                border-radius: 8px;
                padding: 10px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8d62ff, stop:1 #7c4dff);
            }
        """)
        btn_close.clicked.connect(self.accept)
        card_layout.addWidget(btn_close)

        main_layout.addWidget(card)
