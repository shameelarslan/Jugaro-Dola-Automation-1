"""
Main Application Window Container with Professional Top Header Bar,
Left Sidebar Navigation with Developer/About & Contact Us Links,
Bottom User License Card, and Stacked SaaS Page Views for Waqas's Automation Software.
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QListWidget, QListWidgetItem, QStackedWidget,
    QVBoxLayout, QLabel, QFrame, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QKeySequence, QShortcut

from app.gui.theme import DARK_THEME_QSS
from app.gui.views.dashboard_view import DashboardView
from app.gui.views.sessions_view import SessionsView
from app.gui.views.prompts_view import PromptsView
from app.gui.views.automation_view import AutomationView
from app.gui.views.downloads_view import DownloadsView
from app.gui.views.logs_view import LogsView
from app.gui.views.super_admin_view import SuperAdminView
from app.core.database import db
from app.core.admin_manager import admin_manager
from app.core.cloud_manager import cloud_manager
from app.gui.dialogs.auth_dialog import AuthDialog
from app.gui.components.admin_dialog import AdminPasswordDialog
from app.gui.dialogs.about_dialog import AboutDialog
from app.gui.dialogs.contact_dialog import ContactDialog
from app.gui.dialogs.user_profile_dialog import UserProfileDialog
from app.gui.dialogs.update_dialog import UpdateDialog
from app.core.updater import updater
from app.gui.components.network_status_widget import NetworkStatusWidget

def _resolve_logo_path() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass_logo = Path(sys._MEIPASS) / "app" / "gui" / "assets" / "logo.png"
        if meipass_logo.exists():
            return meipass_logo
    return Path(__file__).resolve().parent / "assets" / "logo.png"

LOGO_PATH = _resolve_logo_path()

class MainWindow(QMainWindow):
    def __init__(self, queue_manager, parent=None):
        super().__init__(parent)
        self.queue_manager = queue_manager
        
        self.setWindowTitle("Waqas's Automation Pro — Commercial Desktop Suite v2.0")
        self.resize(1360, 860)
        self.setMinimumSize(1100, 720)
        self.setStyleSheet(DARK_THEME_QSS)

        self._init_ui()

        # Connect QueueManager callback for real-time live metric broadcasts
        self.queue_manager.register_status_callback(self._update_top_header)

        # Global Shortcut Ctrl+Shift+W to toggle Admin Mode
        self.shortcut_admin = QShortcut(QKeySequence("Ctrl+Shift+W"), self)
        self.shortcut_admin.activated.connect(self._on_admin_mode_clicked)

        # Connect Admin Mode state listener for Activity / Logs and Super Admin tab visibility
        admin_manager.mode_changed.connect(self._on_admin_mode_changed)
        self._on_admin_mode_changed(admin_manager.is_admin)

        # 1-second GUI polling timer for live header updates
        self.header_timer = QTimer(self)
        self.header_timer.timeout.connect(self._update_top_header)
        self.header_timer.start(1000)

        # Non-blocking Cloud Auto-Update check 3s after boot
        QTimer.singleShot(3000, self._check_for_updates)

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── 1. Top Header Bar (App Title + Status + Network Monitor) ─────────
        header_bar = QFrame()
        header_bar.setFixedHeight(54)
        header_bar.setStyleSheet("background-color: #0f172a; border-bottom: 1px solid #334155;")
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(18, 8, 18, 8)
        header_layout.setSpacing(14)

        # Logo & App Title
        if LOGO_PATH.exists():
            lbl_logo = QLabel()
            pix = QPixmap(str(LOGO_PATH))
            if not pix.isNull():
                lbl_logo.setPixmap(pix.scaledToHeight(30, Qt.TransformationMode.SmoothTransformation))
                header_layout.addWidget(lbl_logo)

        lbl_app_title = QLabel("Waqas's Automation Pro")
        lbl_app_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #f8fafc;")
        header_layout.addWidget(lbl_app_title)

        header_layout.addSpacing(14)

        # Live Automation Status Badge
        lbl_status_tag = QLabel("Status:")
        lbl_status_tag.setStyleSheet("color: #94a3b8; font-weight: 600; font-size: 12px;")
        
        self.lbl_hdr_status = QLabel("IDLE")
        self.lbl_hdr_status.setStyleSheet("""
            background-color: #334155;
            color: #94a3b8;
            font-weight: bold;
            font-size: 11px;
            padding: 3px 10px;
            border-radius: 10px;
        """)
        header_layout.addWidget(lbl_status_tag)
        header_layout.addWidget(self.lbl_hdr_status)

        header_layout.addStretch()

        # Network Monitor (Online/Offline, Ping ms, Speed quality, Public IP & Location)
        self.network_widget = NetworkStatusWidget()
        header_layout.addWidget(self.network_widget)

        root_layout.addWidget(header_bar)

        # ── 2. Content Body (Sidebar Navigation + Stacked Pages) ─────────────
        body_widget = QWidget()
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Left Sidebar Navigation Panel
        sidebar_panel = QFrame()
        sidebar_panel.setFixedWidth(230)
        sidebar_panel.setStyleSheet("background-color: #1e293b; border-right: 1px solid #334155;")
        sidebar_layout = QVBoxLayout(sidebar_panel)
        sidebar_layout.setContentsMargins(0, 10, 0, 14)
        sidebar_layout.setSpacing(6)

        # Main Nav List Widget (NO SCROLLBAR)
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sidebar.setStyleSheet("""
            QListWidget#sidebar {
                background-color: transparent;
                border: none;
                outline: none;
                font-size: 13px;
                font-weight: 500;
            }
            QListWidget#sidebar::item {
                height: 42px;
                padding-left: 14px;
                color: #94a3b8;
                border-left: 4px solid transparent;
                margin: 2px 8px;
                border-radius: 8px;
            }
            QListWidget#sidebar::item:hover {
                background-color: #334155;
                color: #ffffff;
            }
            QListWidget#sidebar::item:selected {
                background-color: #2563eb;
                color: #ffffff;
                border-left: 4px solid #60a5fa;
                font-weight: 700;
            }
        """)

        nav_items = [
            ("📊  Dashboard", 0),
            ("🔑  Sessions", 1),
            ("📝  Prompts", 2),
            ("⚡  Automation", 3),
            ("📥  Downloads", 4),
            ("📄  Activity / Logs", 5),
            ("👑  Super Admin", 6),
        ]

        for text, idx in nav_items:
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, idx)
            self.sidebar.addItem(item)

        self.sidebar.setMinimumHeight(330)
        sidebar_layout.addWidget(self.sidebar)

        sidebar_layout.addStretch()

        # ── Sidebar Utility Links (About Me & Contact Us) ────────────────────
        util_box = QVBoxLayout()
        util_box.setContentsMargins(10, 0, 10, 8)
        util_box.setSpacing(6)

        # About Me Button
        btn_about = QPushButton("✨  About Developer")
        btn_about.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_about.setStyleSheet("""
            QPushButton {
                background-color: rgba(124, 77, 255, 0.1);
                color: #c7d2fe;
                font-size: 12px;
                font-weight: 700;
                border: 1px solid rgba(124, 77, 255, 0.25);
                text-align: left;
                padding: 8px 14px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(124, 77, 255, 0.25);
                border-color: #7c4dff;
                color: #ffffff;
            }
        """)
        btn_about.clicked.connect(self._open_about_dialog)
        util_box.addWidget(btn_about)

        # Contact Us Button
        btn_contact = QPushButton("💬  Direct Support & Contact")
        btn_contact.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_contact.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 230, 118, 0.08);
                color: #6ee7b7;
                font-size: 12px;
                font-weight: 700;
                border: 1px solid rgba(0, 230, 118, 0.25);
                text-align: left;
                padding: 8px 14px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(0, 230, 118, 0.2);
                border-color: #00e676;
                color: #ffffff;
            }
        """)
        btn_contact.clicked.connect(self._open_contact_dialog)
        util_box.addWidget(btn_contact)

        sidebar_layout.addLayout(util_box)

        # ── Bottom User Profile Card ─────────────────────────────────────────
        user_card_container = QWidget()
        user_card_layout = QVBoxLayout(user_card_container)
        user_card_layout.setContentsMargins(10, 0, 10, 0)

        self.user_card = QFrame()
        self.user_card.setObjectName("UserCard")
        self.user_card.setCursor(Qt.CursorShape.PointingHandCursor)
        self.user_card.setStyleSheet("""
            QFrame#UserCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #14172b, stop:1 #1c213d);
                border: 1px solid rgba(124, 77, 255, 0.4);
                border-radius: 12px;
            }
            QFrame#UserCard:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1c213d, stop:1 #262c52);
                border: 1px solid #7c4dff;
            }
        """)
        self.user_card.mousePressEvent = lambda e: self._open_user_profile()

        card_inner = QHBoxLayout(self.user_card)
        card_inner.setContentsMargins(10, 10, 10, 10)
        card_inner.setSpacing(10)

        # User Avatar Circle
        user = cloud_manager.current_user or {}
        user_email = user.get("email", "guest@waqasautomation.com")
        user_name = user.get("full_name") or user_email.split("@")[0].capitalize()
        initials = (user_name[:2]).upper() if len(user_name) >= 2 else "WA"

        self.lbl_user_avatar = QLabel(initials)
        self.lbl_user_avatar.setFixedSize(38, 38)
        self.lbl_user_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_user_avatar.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7c4dff, stop:1 #3b82f6);
            color: #ffffff;
            font-size: 14px;
            font-weight: 900;
            border-radius: 19px;
            border: 1.5px solid rgba(255, 255, 255, 0.25);
        """)
        card_inner.addWidget(self.lbl_user_avatar)

        # User Info Text & License Pill
        u_vbox = QVBoxLayout()
        u_vbox.setSpacing(3)
        
        self.lbl_card_name = QLabel(user_name)
        self.lbl_card_name.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 800;")
        
        self.lbl_card_license = QLabel("🟢 Free License Activated")
        self.lbl_card_license.setStyleSheet("""
            background-color: rgba(16, 185, 129, 0.15);
            color: #10b981;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 6px;
            border: 1px solid rgba(16, 185, 129, 0.35);
        """)
        
        u_vbox.addWidget(self.lbl_card_name)
        u_vbox.addWidget(self.lbl_card_license)
        card_inner.addLayout(u_vbox)

        card_inner.addStretch()

        lbl_chevron = QLabel("›")
        lbl_chevron.setStyleSheet("color: #8f9bb3; font-size: 20px; font-weight: 700;")
        card_inner.addWidget(lbl_chevron)

        user_card_layout.addWidget(self.user_card)
        sidebar_layout.addWidget(user_card_container)

        body_layout.addWidget(sidebar_panel)

        # Stacked Views Container
        self.stack = QStackedWidget()

        self.view_dashboard = DashboardView(self.queue_manager)
        self.view_sessions = SessionsView()
        self.view_prompts = PromptsView()
        self.view_automation = AutomationView(self.queue_manager)
        self.view_downloads = DownloadsView(self.queue_manager)
        self.view_logs = LogsView()
        self.view_super_admin = SuperAdminView()

        self.stack.addWidget(self.view_dashboard)
        self.stack.addWidget(self.view_sessions)
        self.stack.addWidget(self.view_prompts)
        self.stack.addWidget(self.view_automation)
        self.stack.addWidget(self.view_downloads)
        self.stack.addWidget(self.view_logs)
        self.stack.addWidget(self.view_super_admin)

        body_layout.addWidget(self.stack, stretch=1)
        root_layout.addWidget(body_widget, stretch=1)

        self.sidebar.currentRowChanged.connect(self._on_tab_switched)
        self.sidebar.setCurrentRow(0)

    def _open_about_dialog(self):
        try:
            dlg = AboutDialog(self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open About dialog: {e}")

    def _open_contact_dialog(self):
        try:
            dlg = ContactDialog(self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open Contact dialog: {e}")

    def _open_user_profile(self):
        try:
            dlg = UserProfileDialog(self)
            dlg.sign_out_requested.connect(self._handle_logout)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open User Profile: {e}")

    def _on_tab_switched(self, index: int):
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.view_dashboard._auto_scroll_enabled = True
            self.view_dashboard.lbl_autoscroll_status.setText("● Auto-scroll: ON")
            self.view_dashboard.lbl_autoscroll_status.setStyleSheet("color: #10b981; font-size: 10px; font-weight: bold;")
            self.view_dashboard._is_programmatic_scroll = True
            sb = self.view_dashboard.txt_logs.verticalScrollBar()
            sb.setValue(sb.maximum())
            self.view_dashboard._is_programmatic_scroll = False
        elif index == 5:
            self.view_logs._auto_scroll_enabled = True
            self.view_logs.lbl_autoscroll_status.setText("● Auto-scroll: ON")
            self.view_logs.lbl_autoscroll_status.setStyleSheet("color: #10b981; font-size: 11px; font-weight: bold; padding: 4px 8px; background-color: #0f172a; border-radius: 4px; border: 1px solid #1e293b;")
            self.view_logs._is_programmatic_scroll = True
            sb = self.view_logs.txt_console.verticalScrollBar()
            sb.setValue(sb.maximum())
            self.view_logs._is_programmatic_scroll = False
        elif index == 6:
            # Auto-refresh Super Admin analytics when tab opened
            self.view_super_admin.refresh_stats()

    def _update_top_header(self):
        """Refreshes header status badge live."""
        stats = self.queue_manager.get_batch_summary_stats()
        pending = stats.get("pending", 0)
        completed = stats.get("completed", 0)
        failed = stats.get("failed", 0)

        if self.queue_manager._stop_requested:
            self.lbl_hdr_status.setText("STOPPED")
            self.lbl_hdr_status.setStyleSheet("background-color: #7f1d1d; color: #fca5a5; font-weight: bold; padding: 3px 10px; border-radius: 10px;")
        elif self.queue_manager._is_running:
            if self.queue_manager._is_paused:
                self.lbl_hdr_status.setText("PAUSED")
                self.lbl_hdr_status.setStyleSheet("background-color: #78350f; color: #fde68a; font-weight: bold; padding: 3px 10px; border-radius: 10px;")
            else:
                self.lbl_hdr_status.setText("RUNNING")
                self.lbl_hdr_status.setStyleSheet("background-color: #14532d; color: #86efac; font-weight: bold; padding: 3px 10px; border-radius: 10px;")
        elif completed > 0 and pending == 0:
            self.lbl_hdr_status.setText("COMPLETED")
            self.lbl_hdr_status.setStyleSheet("background-color: #1e3a8a; color: #93c5fd; font-weight: bold; padding: 3px 10px; border-radius: 10px;")
        elif failed > 0 and pending == 0:
            self.lbl_hdr_status.setText("ERROR")
            self.lbl_hdr_status.setStyleSheet("background-color: #7f1d1d; color: #fca5a5; font-weight: bold; padding: 3px 10px; border-radius: 10px;")
        else:
            self.lbl_hdr_status.setText("IDLE")
            self.lbl_hdr_status.setStyleSheet("background-color: #334155; color: #94a3b8; font-weight: bold; padding: 3px 10px; border-radius: 10px;")

        # Live refresh of SessionsView table states
        if hasattr(self, "view_sessions"):
            self.view_sessions.load_sessions()

    def _on_admin_mode_clicked(self):
        """Toggles or prompts password for Admin Mode (Shortcut: Ctrl+Shift+W)."""
        if admin_manager.is_admin:
            admin_manager.lock_user_mode()
            QMessageBox.information(self, "User Mode", "Switched back to USER MODE.\nRaw internal diagnostics and Super Admin panel are now hidden.")
        else:
            dlg = AdminPasswordDialog(self)
            if dlg.exec():
                QMessageBox.information(self, "Admin Access Granted", "👑 ADMIN MODE UNLOCKED!\nSuper Admin Cloud Dashboard, Activity Logs, and Watermark Tuners are now active.")

    def _on_admin_mode_changed(self, is_admin: bool):
        """Controls visibility of the Activity / Logs and Super Admin tabs in sidebar (Admin Mode only)."""
        if hasattr(self, "sidebar"):
            self.sidebar.setRowHidden(5, not is_admin)
            self.sidebar.setRowHidden(6, not is_admin)
            if not is_admin and self.sidebar.currentRow() in [5, 6]:
                self.sidebar.setCurrentRow(0)

    def _handle_logout(self):
        """Logs out user and re-prompts auth dialog."""
        reply = QMessageBox.question(
            self, "Sign Out", "Are you sure you want to sign out?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            cloud_manager.logout()
            self.hide()
            dlg = AuthDialog()
            if dlg.exec():
                user = cloud_manager.current_user or {}
                user_name = user.get("full_name") or user.get("email", "Guest").split("@")[0].capitalize()
                self.lbl_card_name.setText(user_name)
                self.lbl_user_avatar.setText((user_name[:2]).upper() if len(user_name) >= 2 else "WA")
                self.show()
            else:
                self.close()

    def _check_for_updates(self):
        """Non-blocking background check for newer releases in Supabase Cloud."""
        try:
            is_avail, release = updater.check_for_updates()
            if is_avail and release:
                dlg = UpdateDialog(release, self)
                dlg.exec()
        except Exception:
            pass

    def closeEvent(self, event):
        try:
            if hasattr(self, "network_widget"):
                self.network_widget.thread.stop()
        except Exception:
            pass
        super().closeEvent(event)
