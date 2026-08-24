"""
Simplified Professional Session Management View for Waqas's Automation Software.
Features clean 5-column table (Select, Session ID, Session Name, Status, Actions),
bright AVAILABLE / EXPIRED status badges, and a non-blocking manual OPEN inspection button.
"""

import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox, QGroupBox, QComboBox,
    QDialog, QDialogButtonBox, QFormLayout, QCheckBox, QMenu
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QAction
from app.core.database import db
from app.managers.session_manager import SessionManager

class AddSessionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Dola Session")
        self.setMinimumWidth(480)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        form = QFormLayout()

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("e.g. Dola Session 01")

        self.cbo_type = QComboBox()
        self.cbo_type.addItems(["JSON Cookies", "Chrome Profile Directory"])

        self.txt_payload = QTextEdit()
        self.txt_payload.setPlaceholderText("Paste JSON cookies array or enter profile path...")

        form.addRow("Session Name:", self.txt_name)
        form.addRow("Session Type:", self.cbo_type)
        form.addRow("Cookie Data / Path:", self.txt_payload)

        layout.addLayout(form)

        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bbox.accepted.connect(self._validate_and_accept)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

    def _validate_and_accept(self):
        if not self.txt_name.text().strip():
            QMessageBox.warning(self, "Validation", "Please provide a session name.")
            return
        if not self.txt_payload.toPlainText().strip():
            QMessageBox.warning(self, "Validation", "Please provide cookie data or a profile directory.")
            return
        self.accept()

    def get_data(self):
        stype = "profile_dir" if self.cbo_type.currentIndex() == 1 else "cookies_json"
        text_val = self.txt_payload.toPlainText().strip()
        return {
            "name": self.txt_name.text().strip(),
            "session_type": stype,
            "cookie_data": text_val if stype == "cookies_json" else None,
            "profile_path": text_val if stype == "profile_dir" else None
        }

class SessionsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._checked_session_ids = set()
        self._last_sessions_sig = None
        self._init_ui()
        self.load_sessions(force=True)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_sessions)
        self.timer.start(4000)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_sessions(force=False)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # ── 1. Top Header Bar ────────────────────────────────────────────────
        hdr_layout = QHBoxLayout()
        lbl_title = QLabel("Session Management")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #f8fafc;")

        self.lbl_count = QLabel("0 Available | 0 Expired (0 Total)")
        self.lbl_count.setStyleSheet("color: #94a3b8; font-size: 13px;")

        hdr_layout.addWidget(lbl_title)
        hdr_layout.addSpacing(16)
        hdr_layout.addWidget(self.lbl_count)
        hdr_layout.addStretch()

        btn_add = QPushButton("+ Add Session")
        btn_add.setObjectName("btn_success")
        btn_add.clicked.connect(self._on_add_session)

        btn_import = QPushButton("📥 Import JSON")
        btn_import.setObjectName("btn_secondary")
        btn_import.clicked.connect(self._on_import_cookies)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setObjectName("btn_secondary")
        btn_refresh.clicked.connect(self.load_sessions)

        hdr_layout.addWidget(btn_add)
        hdr_layout.addWidget(btn_import)
        hdr_layout.addWidget(btn_refresh)
        main_layout.addLayout(hdr_layout)

        # ── 2. Table Selection Toolbar ───────────────────────────────────────
        bar_layout = QHBoxLayout()
        btn_select_all = QPushButton("Select All Available")
        btn_select_all.setFixedHeight(28)
        btn_select_all.clicked.connect(self._select_all)

        btn_deselect_all = QPushButton("Deselect All")
        btn_deselect_all.setFixedHeight(28)
        btn_deselect_all.clicked.connect(self._deselect_all)

        btn_delete_selected = QPushButton("🗑 Delete Selected")
        btn_delete_selected.setFixedHeight(28)
        btn_delete_selected.setObjectName("btn_danger")
        btn_delete_selected.clicked.connect(self._delete_selected)

        lbl_hint = QLabel("💡 Tip: Right-click any row to Mark Available / Expired or Open Browser.")
        lbl_hint.setStyleSheet("color: #64748b; font-size: 11px; font-style: italic;")

        bar_layout.addWidget(btn_select_all)
        bar_layout.addWidget(btn_deselect_all)
        bar_layout.addSpacing(12)
        bar_layout.addWidget(btn_delete_selected)
        bar_layout.addSpacing(16)
        bar_layout.addWidget(lbl_hint)
        bar_layout.addStretch()
        main_layout.addLayout(bar_layout)

        # ── 3. Available Sessions Table ──────────────────────────────────────
        self.grp_available = QGroupBox("🟢 Available Sessions (0)")
        self.grp_available.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                color: #10b981;
                border: 1px solid #1e293b;
                border-radius: 8px;
                margin-top: 6px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
        """)
        layout_avail = QVBoxLayout(self.grp_available)
        layout_avail.setContentsMargins(8, 14, 8, 8)

        self.table_available = QTableWidget()
        self._setup_table(self.table_available)
        self.table_available.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_available.customContextMenuRequested.connect(self._show_available_context_menu)
        layout_avail.addWidget(self.table_available)
        main_layout.addWidget(self.grp_available, stretch=1)

        # ── 4. Expired Sessions Table ────────────────────────────────────────
        self.grp_expired = QGroupBox("🔴 Expired Sessions (0)")
        self.grp_expired.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                color: #ef4444;
                border: 1px solid #1e293b;
                border-radius: 8px;
                margin-top: 6px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
        """)
        layout_exp = QVBoxLayout(self.grp_expired)
        layout_exp.setContentsMargins(8, 14, 8, 8)

        self.table_expired = QTableWidget()
        self._setup_table(self.table_expired)
        self.table_expired.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_expired.customContextMenuRequested.connect(self._show_expired_context_menu)
        layout_exp.addWidget(self.table_expired)
        main_layout.addWidget(self.grp_expired, stretch=1)

    def _setup_table(self, table: QTableWidget):
        """Configures standard 6-column layout for session tables."""
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Select", "Session ID", "Session Name", "Videos Left", "Status", "Actions"
        ])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

    def _collect_checked_ids(self):
        """Preserves checked checkbox states before table repainting."""
        for tbl in (self.table_available, self.table_expired):
            for r in range(tbl.rowCount()):
                chk = tbl.cellWidget(r, 0)
                sid_item = tbl.item(r, 1)
                if chk and isinstance(chk, QCheckBox) and sid_item:
                    try:
                        s_id = int(sid_item.text())
                        if chk.isChecked():
                            self._checked_session_ids.add(s_id)
                        else:
                            self._checked_session_ids.discard(s_id)
                    except Exception:
                        pass

    def load_sessions(self, force: bool = False):
        """Loads sessions from SQLite and renders Available and Expired sessions in separate tables."""
        if not force and not self.isVisible():
            return

        # Check and restore any sessions whose 24-hour cooldown has elapsed
        try:
            db.reset_expired_sessions()
        except Exception:
            pass

        sessions = db.get_all_sessions()
        sig = tuple((s["id"], s.get("status"), s.get("name"), s.get("videos_left")) for s in sessions)
        if not force and sig == self._last_sessions_sig:
            return
        self._last_sessions_sig = sig

        self._collect_checked_ids()

        available_sessions = []
        expired_sessions = []

        for s in sessions:
            st = (s.get("status") or "Available").upper()
            if st in ("AVAILABLE", "IDLE", "RUNNING", "BUSY"):
                available_sessions.append(s)
            else:
                expired_sessions.append(s)

        self.lbl_count.setText(f"{len(available_sessions)} Available | {len(expired_sessions)} Expired ({len(sessions)} Total)")
        self.grp_available.setTitle(f"🟢 Available Sessions ({len(available_sessions)})")
        self.grp_expired.setTitle(f"🔴 Expired Sessions ({len(expired_sessions)})")

        self._populate_table(self.table_available, available_sessions, is_available=True)
        self._populate_table(self.table_expired, expired_sessions, is_available=False)

    def _populate_table(self, table: QTableWidget, session_list: list, is_available: bool):
        table.setUpdatesEnabled(False)
        table.blockSignals(True)
        try:
            table.setRowCount(len(session_list))

            for row, s in enumerate(session_list):
                sid = s["id"]
                chk = QCheckBox()
                chk.setChecked(sid in self._checked_session_ids)
                chk.setStyleSheet("margin-left: 14px;")

                def _make_toggle_handler(session_id):
                    return lambda checked: (
                        self._checked_session_ids.add(session_id) if checked
                        else self._checked_session_ids.discard(session_id)
                    )
                chk.toggled.connect(_make_toggle_handler(sid))
                table.setCellWidget(row, 0, chk)

                # Session ID
                item_id = QTableWidgetItem(str(sid))
                item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, 1, item_id)

                # Session Name
                item_name = QTableWidgetItem(s["name"])
                font = item_name.font()
                font.setBold(True)
                item_name.setFont(font)
                table.setItem(row, 2, item_name)

                # Videos Left Column
                v_left = s.get("videos_left", 15) if s.get("videos_left") is not None else 15
                item_vl = QTableWidgetItem(f"⚡ {v_left} Left")
                item_vl.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item_vl.setForeground(QColor("#38bdf8") if v_left > 0 else QColor("#ef4444"))
                font_vl = item_vl.font()
                font_vl.setBold(True)
                item_vl.setFont(font_vl)
                table.setItem(row, 3, item_vl)

                # Status Badge
                raw_status = (s.get("status") or ("Available" if is_available else "Expired")).upper()
                if is_available:
                    status_label = "AVAILABLE" if raw_status != "RUNNING" else "RUNNING"
                    status_color = "#10b981" if raw_status != "RUNNING" else "#3b82f6"
                else:
                    status_label = "EXPIRED"
                    status_color = "#ef4444"

                item_status = QTableWidgetItem(status_label)
                item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item_status.setForeground(QColor(status_color))
                font_st = item_status.font()
                font_st.setBold(True)
                item_status.setFont(font_st)
                table.setItem(row, 4, item_status)

                # Actions Column: Manual OPEN Button
                btn_open = QPushButton("🔍 OPEN")
                btn_open.setFixedHeight(24)
                btn_open.setStyleSheet("""
                    QPushButton {
                        background-color: #1e293b;
                        color: #38bdf8;
                        border: 1px solid #0284c7;
                        border-radius: 4px;
                        font-weight: 600;
                        padding: 2px 12px;
                    }
                    QPushButton:hover {
                        background-color: #0284c7;
                        color: #ffffff;
                    }
                """)
                btn_open.clicked.connect(lambda _, sess_id=sid: self._open_manual_session(sess_id))
                table.setCellWidget(row, 5, btn_open)
        finally:
            table.blockSignals(False)
            table.setUpdatesEnabled(True)

    # ── Context Menus (Right-Click Handlers) ──────────────────────────────────
    def _show_available_context_menu(self, pos):
        item = self.table_available.itemAt(pos)
        if not item:
            return
        row = item.row()
        sid_item = self.table_available.item(row, 1)
        if not sid_item:
            return
        try:
            sid = int(sid_item.text())
        except ValueError:
            return

        menu = QMenu(self)
        menu.setStyleSheet(self._menu_style())

        act_expire = menu.addAction("✕ Mark as Expired")
        menu.addSeparator()
        act_open = menu.addAction("🔍 Open Browser (Inspect)")
        act_delete = menu.addAction("🗑 Delete Session")

        action = menu.exec(self.table_available.viewport().mapToGlobal(pos))
        if action == act_expire:
            SessionManager.make_session_expired(sid)
            self.load_sessions()
        elif action == act_open:
            self._open_manual_session(sid)
        elif action == act_delete:
            self._delete_single_session(sid)

    def _show_expired_context_menu(self, pos):
        item = self.table_expired.itemAt(pos)
        if not item:
            return
        row = item.row()
        sid_item = self.table_expired.item(row, 1)
        if not sid_item:
            return
        try:
            sid = int(sid_item.text())
        except ValueError:
            return

        menu = QMenu(self)
        menu.setStyleSheet(self._menu_style())

        act_available = menu.addAction("✓ Mark as Available")
        menu.addSeparator()
        act_open = menu.addAction("🔍 Open Browser (Inspect)")
        act_delete = menu.addAction("🗑 Delete Session")

        action = menu.exec(self.table_expired.viewport().mapToGlobal(pos))
        if action == act_available:
            SessionManager.make_session_available(sid)
            self.load_sessions()
        elif action == act_open:
            self._open_manual_session(sid)
        elif action == act_delete:
            self._delete_single_session(sid)

    def _menu_style(self) -> str:
        return """
            QMenu {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 18px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3b82f6;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: #334155;
                margin: 4px 8px;
            }
        """

    def get_selected_sessions(self) -> list:
        """Returns ONLY the list of Available session dicts explicitly checked by the user."""
        selected = []
        for sid in sorted(self._checked_session_ids):
            sess = db.get_session(sid)
            if sess and (sess.get("status") or "Available").upper() in ("AVAILABLE", "RUNNING", "IDLE"):
                selected.append(sess)
        return selected

    def _open_manual_session(self, session_id: int):
        """Launches an isolated visible browser for manual inspection of Dola session."""
        try:
            SessionManager.launch_manual_browser_async(session_id)
        except Exception as e:
            QMessageBox.critical(self, "Browser Error", f"Could not launch manual browser: {e}")

    def _select_all(self):
        """Selects all sessions in the Available table."""
        for r in range(self.table_available.rowCount()):
            chk = self.table_available.cellWidget(r, 0)
            sid_item = self.table_available.item(r, 1)
            if chk and sid_item:
                chk.setChecked(True)
                self._checked_session_ids.add(int(sid_item.text()))

    def _deselect_all(self):
        """Deselects all sessions across both tables."""
        for tbl in (self.table_available, self.table_expired):
            for r in range(tbl.rowCount()):
                chk = tbl.cellWidget(r, 0)
                sid_item = tbl.item(r, 1)
                if chk and sid_item:
                    chk.setChecked(False)
                    self._checked_session_ids.discard(int(sid_item.text()))

    def _delete_single_session(self, session_id: int):
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete session #{session_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            db.delete_session(session_id)
            self._checked_session_ids.discard(session_id)
            self.load_sessions()

    def _delete_selected(self):
        self._collect_checked_ids()
        to_del = list(self._checked_session_ids)

        if not to_del:
            QMessageBox.information(self, "Notice", "No sessions selected for deletion.")
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete {len(to_del)} selected session(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            for sid in to_del:
                db.delete_session(sid)
            self._checked_session_ids.clear()
            self.load_sessions()

    def _on_add_session(self):
        dlg = AddSessionDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            db.add_session(
                name=data["name"],
                session_type=data["session_type"],
                cookie_data=data["cookie_data"],
                profile_path=data["profile_path"]
            )
            self.load_sessions()

    def _on_import_cookies(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Cookies JSON File(s) in Bulk", "", "JSON Files (*.json);;All Files (*.*)"
        )
        if file_paths:
            success_count = 0
            errors = []
            for file_path in file_paths:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                    name = Path(file_path).stem
                    db.add_session(name=name, session_type="cookies_json", cookie_data=content)
                    success_count += 1
                except Exception as e:
                    errors.append(f"{Path(file_path).name}: {e}")

            self.load_sessions(force=True)

            if success_count > 0 and not errors:
                QMessageBox.information(
                    self, "Bulk Import Success",
                    f"Successfully imported {success_count} session(s) in bulk!"
                )
            elif success_count > 0 and errors:
                QMessageBox.warning(
                    self, "Partial Bulk Import",
                    f"Successfully imported {success_count} session(s).\n\nFailed files:\n" + "\n".join(errors[:5])
                )
            elif errors:
                QMessageBox.critical(
                    self, "Bulk Import Error",
                    f"Failed to import selected files:\n" + "\n".join(errors[:5])
                )
