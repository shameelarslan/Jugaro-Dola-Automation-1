"""
User Authentication Dialog - Premium Dark Glassmorphic Login & Signup Window.
Connects users directly with Supabase Cloud.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFrame, QStackedWidget, QWidget, QMessageBox, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon
from app.core.cloud_manager import cloud_manager

class AuthDialog(QDialog):
    login_successful = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Waqas Automation - Cloud Account")
        self.setFixedSize(440, 520)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Card Container
        self.card = QFrame()
        self.card.setObjectName("AuthCard")
        self.card.setStyleSheet("""
            QFrame#AuthCard {
                background-color: #121420;
                border: 1px solid rgba(124, 77, 255, 0.35);
                border-radius: 16px;
            }
        """)

        # Drop Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(124, 77, 255, 90))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(14)

        # Header Title
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        
        self.lbl_brand = QLabel("🚀 WAQAS AUTOMATION")
        self.lbl_brand.setStyleSheet("color: #7c4dff; font-weight: 900; font-size: 13px; letter-spacing: 1.5px;")
        self.lbl_brand.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_heading = QLabel("Sign In to Your Account")
        self.lbl_heading.setStyleSheet("color: #ffffff; font-weight: 800; font-size: 20px;")
        self.lbl_heading.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_sub = QLabel("Enter your credentials to continue")
        self.lbl_sub.setStyleSheet("color: #8f9bb3; font-size: 12px;")
        self.lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_box.addWidget(self.lbl_brand)
        title_box.addWidget(self.lbl_heading)
        title_box.addWidget(self.lbl_sub)
        card_layout.addLayout(title_box)

        # Message / Status Box
        self.lbl_msg = QLabel("")
        self.lbl_msg.setStyleSheet("color: #ff5252; font-size: 12px; font-weight: 600;")
        self.lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_msg.setWordWrap(True)
        self.lbl_msg.setVisible(False)
        card_layout.addWidget(self.lbl_msg)

        # Form Inputs Container
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Full Name (e.g. Ali Khan)")
        self._style_input(self.input_name)
        self.input_name.setVisible(False)

        # WhatsApp Number Input (Signup only)
        self.input_whatsapp = QLineEdit()
        self.input_whatsapp.setPlaceholderText("📱 WhatsApp Number (e.g. +923001234567)")
        self._style_input(self.input_whatsapp)
        self.input_whatsapp.setVisible(False)

        self.input_email = QLineEdit()
        self.input_email.setPlaceholderText("Email Address")
        self._style_input(self.input_email)

        # Password field with eye toggle
        self.password_container = QFrame()
        self.password_container.setStyleSheet("background: transparent; border: none;")
        pwd_layout = QHBoxLayout(self.password_container)
        pwd_layout.setContentsMargins(0, 0, 0, 0)
        pwd_layout.setSpacing(6)

        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Password")
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._style_input(self.input_password)

        self.btn_eye_password = QPushButton("👁")
        self._style_eye_button(self.btn_eye_password)
        self.btn_eye_password.clicked.connect(lambda: self._toggle_password_visibility(self.input_password, self.btn_eye_password))

        pwd_layout.addWidget(self.input_password)
        pwd_layout.addWidget(self.btn_eye_password)

        # Confirm Password field with eye toggle (Signup only)
        self.confirm_password_container = QFrame()
        self.confirm_password_container.setStyleSheet("background: transparent; border: none;")
        cpwd_layout = QHBoxLayout(self.confirm_password_container)
        cpwd_layout.setContentsMargins(0, 0, 0, 0)
        cpwd_layout.setSpacing(6)

        self.input_confirm_password = QLineEdit()
        self.input_confirm_password.setPlaceholderText("Confirm Password")
        self.input_confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._style_input(self.input_confirm_password)

        self.btn_eye_confirm = QPushButton("👁")
        self._style_eye_button(self.btn_eye_confirm)
        self.btn_eye_confirm.clicked.connect(lambda: self._toggle_password_visibility(self.input_confirm_password, self.btn_eye_confirm))

        cpwd_layout.addWidget(self.input_confirm_password)
        cpwd_layout.addWidget(self.btn_eye_confirm)
        self.confirm_password_container.setVisible(False)

        card_layout.addWidget(self.input_name)
        card_layout.addWidget(self.input_whatsapp)
        card_layout.addWidget(self.input_email)
        card_layout.addWidget(self.password_container)
        card_layout.addWidget(self.confirm_password_container)

        card_layout.addSpacing(6)

        # Action Button (Login / Sign Up)
        self.btn_submit = QPushButton("Sign In")
        self.btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_submit.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c4dff, stop:1 #651fff);
                color: #ffffff;
                font-size: 14px;
                font-weight: 800;
                border-radius: 10px;
                padding: 12px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8d62ff, stop:1 #7c4dff);
            }
            QPushButton:disabled {
                background-color: #333950;
                color: #777d95;
            }
        """)
        self.btn_submit.clicked.connect(self._handle_submit)
        card_layout.addWidget(self.btn_submit)

        # Toggle Link (Login <-> Signup)
        self.btn_toggle = QPushButton("Don't have an account? Create one")
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #9d7aff;
                font-size: 12px;
                font-weight: 600;
                border: none;
                text-decoration: underline;
                padding: 4px;
            }
            QPushButton:hover {
                color: #bfa8ff;
            }
        """)
        self.btn_toggle.clicked.connect(self._toggle_mode)
        card_layout.addWidget(self.btn_toggle)

        card_layout.addStretch()

        # Close / Cancel Button
        self.btn_close = QPushButton("✕ Exit")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #64748b;
                font-size: 12px;
                font-weight: 600;
                border: none;
            }
            QPushButton:hover {
                color: #ef4444;
            }
        """)
        self.btn_close.clicked.connect(self.reject)
        card_layout.addWidget(self.btn_close, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(self.card)

        self.is_signup_mode = False

    def _style_input(self, widget: QLineEdit):
        widget.setStyleSheet("""
            QLineEdit {
                background-color: #1a1d2e;
                color: #ffffff;
                font-size: 13px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 11px 14px;
            }
            QLineEdit:focus {
                border: 1px solid #7c4dff;
                background-color: #1f2338;
            }
        """)

    def _style_eye_button(self, btn: QPushButton):
        """Styles the password visibility toggle (eye) button."""
        btn.setFixedSize(40, 40)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #1a1d2e;
                color: #8f9bb3;
                font-size: 16px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #1f2338;
                border: 1px solid #7c4dff;
                color: #ffffff;
            }
        """)

    def _toggle_password_visibility(self, input_field: QLineEdit, btn: QPushButton):
        """Toggles password field between visible and hidden."""
        if input_field.echoMode() == QLineEdit.EchoMode.Password:
            input_field.setEchoMode(QLineEdit.EchoMode.Normal)
            btn.setText("🙈")
        else:
            input_field.setEchoMode(QLineEdit.EchoMode.Password)
            btn.setText("👁")

    def _toggle_mode(self):
        self.is_signup_mode = not self.is_signup_mode
        self.lbl_msg.setVisible(False)

        if self.is_signup_mode:
            self.lbl_heading.setText("Create Free Account")
            self.lbl_sub.setText("Sign up to access Waqas Automation")
            self.btn_submit.setText("Register Account")
            self.btn_toggle.setText("Already have an account? Sign In")
            self.input_name.setVisible(True)
            self.input_whatsapp.setVisible(True)
            self.confirm_password_container.setVisible(True)
            self.setFixedSize(440, 680)
        else:
            self.lbl_heading.setText("Sign In to Your Account")
            self.lbl_sub.setText("Enter your credentials to continue")
            self.btn_submit.setText("Sign In")
            self.btn_toggle.setText("Don't have an account? Create one")
            self.input_name.setVisible(False)
            self.input_whatsapp.setVisible(False)
            self.confirm_password_container.setVisible(False)
            self.setFixedSize(440, 520)

    def _show_msg(self, text: str, is_error: bool = True):
        color = "#ff5252" if is_error else "#00e676"
        self.lbl_msg.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600;")
        self.lbl_msg.setText(text)
        self.lbl_msg.setVisible(True)

    def _handle_submit(self):
        email = self.input_email.text().strip()
        password = self.input_password.text()

        if not email or "@" not in email:
            self._show_msg("Please enter a valid email address.")
            return

        if len(password) < 6:
            self._show_msg("Password must be at least 6 characters long.")
            return

        self.btn_submit.setEnabled(False)
        self.btn_submit.setText("Connecting...")

        if self.is_signup_mode:
            confirm_pwd = self.input_confirm_password.text()
            name = self.input_name.text().strip()
            whatsapp = self.input_whatsapp.text().strip()

            if not whatsapp:
                self._show_msg("WhatsApp number is required.")
                self.btn_submit.setEnabled(True)
                self.btn_submit.setText("Register Account")
                return

            if password != confirm_pwd:
                self._show_msg("Passwords do not match.")
                self.btn_submit.setEnabled(True)
                self.btn_submit.setText("Register Account")
                return

            ok, msg, status = cloud_manager.signup(email, password, name, whatsapp)
            if ok:
                if status == "Active":
                    self._show_msg("Admin account activated! Logging in...", is_error=False)
                    QTimer.singleShot(600, self._on_success)
                else:
                    self._show_msg("🎉 Account created! Waiting for Admin Approval.\nPlease contact Admin Waqas to activate.", is_error=False)
                    self.btn_submit.setEnabled(True)
                    self.btn_submit.setText("Register Account")
                    # Switch to sign in mode after 2.5s
                    QTimer.singleShot(2500, self._toggle_mode)
            else:
                self._show_msg(msg, is_error=True)
                self.btn_submit.setEnabled(True)
                self.btn_submit.setText("Register Account")
        else:
            ok, msg = cloud_manager.login(email, password)
            if ok:
                self._show_msg("Login successful!", is_error=False)
                QTimer.singleShot(600, self._on_success)
            else:
                self._show_msg(msg, is_error=True)
                self.btn_submit.setEnabled(True)
                self.btn_submit.setText("Sign In")

    def _on_success(self):
        user = cloud_manager.current_user
        self.login_successful.emit(user or {})
        self.accept()
