"""
Admin Mode Authentication Dialog with Master Password Verification.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame
)
from PyQt6.QtCore import Qt
from app.core.admin_manager import admin_manager

class AdminPasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔐 Administrator Authentication")
        self.setFixedSize(440, 240)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 10px;
            }
            QLabel {
                color: #f8fafc;
            }
            QLineEdit {
                background-color: #020617;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                color: #f8fafc;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #6366f1;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header Title
        lbl_title = QLabel("👑 Unlock Admin Diagnostics")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #facc15;")
        layout.addWidget(lbl_title)

        lbl_desc = QLabel("Enter your Admin Master Password to access raw technical logs, retry details, and worker diagnostics.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-size: 12px; color: #94a3b8; line-height: 1.4;")
        layout.addWidget(lbl_desc)

        # Password input
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("Enter Admin Password...")
        self.txt_password.returnPressed.connect(self._on_unlock)
        layout.addWidget(self.txt_password)

        # Error label
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: bold;")
        self.lbl_error.setVisible(False)
        layout.addWidget(self.lbl_error)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(34)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 0 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #f8fafc;
            }
        """)
        btn_cancel.clicked.connect(self.reject)

        self.btn_unlock = QPushButton("🔓 Unlock Admin Mode")
        self.btn_unlock.setFixedHeight(34)
        self.btn_unlock.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #6366f1);
                color: #ffffff;
                border: 1px solid #818cf8;
                border-radius: 6px;
                padding: 0 20px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338ca, stop:1 #4f46e5);
            }
        """)
        self.btn_unlock.clicked.connect(self._on_unlock)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addSpacing(10)
        btn_layout.addWidget(self.btn_unlock)
        layout.addLayout(btn_layout)

    def _on_unlock(self):
        pwd = self.txt_password.text()
        if admin_manager.unlock_admin_mode(pwd):
            self.accept()
        else:
            self.lbl_error.setText("❌ Invalid Admin Password. Access Denied.")
            self.lbl_error.setVisible(True)
            self.txt_password.selectAll()
            self.txt_password.setFocus()
