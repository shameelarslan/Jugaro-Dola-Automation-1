"""
Dedicated Automation Control & Settings View.
Provides Video Model selection (Seedance 2.5), Aspect Ratio (9:16),
Videos Per Session (1-15), Sessions At A Time (1-50),
instant setting persistence, validation modal, and primary action controls.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QSpinBox,
    QGroupBox, QMessageBox, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QCheckBox, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont

from app.core.config import AppConfig
from app.core.database import db
from app.core.logger import logger
from app.core.queue_manager import QueueManager
from app.core.admin_manager import admin_manager

class SessionSelectionDialog(QDialog):
    def __init__(self, available_sessions: list, target_total_sessions: int, sessions_at_a_time: int, videos_per_session: int, pending_prompts_count: int, parent=None):
        super().__init__(parent)
        self.available_sessions = available_sessions
        self.target_total_sessions = max(1, target_total_sessions)
        self.sessions_at_a_time = max(1, sessions_at_a_time)
        self.videos_per_session = max(1, videos_per_session)
        self.pending_prompts_count = pending_prompts_count
        self.selected_sessions = []

        # Pre-select up to target_total_sessions from available sessions
        preselected_count = min(self.target_total_sessions, len(available_sessions))
        self._checked_ids = set(s["id"] for s in available_sessions[:preselected_count])

        self.setWindowTitle("Select Sessions for Automation")
        self.resize(660, 540)
        self.setModal(True)
        self._init_ui()
        self._update_capacity_display()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header
        lbl_title = QLabel("Select Active Sessions for Automation Batch")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f8fafc;")
        lbl_sub = QLabel(f"Showing {len(self.available_sessions)} Available session(s). Choose sessions for this rolling batch:")
        lbl_sub.setStyleSheet("color: #94a3b8; font-size: 12px;")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_sub)

        # Capacity & Workload Info Card
        self.capacity_card = QFrame()
        self.capacity_card.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        cap_layout = QVBoxLayout(self.capacity_card)
        cap_layout.setContentsMargins(12, 10, 12, 10)
        cap_layout.setSpacing(4)

        self.lbl_cap_stats = QLabel()
        self.lbl_cap_stats.setStyleSheet("font-size: 12px; font-weight: bold; color: #f8fafc;")

        self.lbl_cap_note = QLabel()
        self.lbl_cap_note.setStyleSheet("font-size: 11px; font-weight: 500;")

        cap_layout.addWidget(self.lbl_cap_stats)
        cap_layout.addWidget(self.lbl_cap_note)
        layout.addWidget(self.capacity_card)

        # Toolbar
        bar = QHBoxLayout()
        btn_sel_all = QPushButton("Select All")
        btn_sel_all.setFixedHeight(26)
        btn_sel_all.clicked.connect(self._select_all)

        btn_desel_all = QPushButton("Deselect All")
        btn_desel_all.setFixedHeight(26)
        btn_desel_all.clicked.connect(self._deselect_all)

        self.lbl_selected_count = QLabel(f"{len(self._checked_ids)} selected")
        self.lbl_selected_count.setStyleSheet("color: #10b981; font-weight: 600; font-size: 12px;")

        bar.addWidget(btn_sel_all)
        bar.addWidget(btn_desel_all)
        bar.addSpacing(10)
        bar.addWidget(self.lbl_selected_count)
        bar.addStretch()
        layout.addLayout(bar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Select", "Session ID", "Session Name", "Videos Left", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        self.table.setRowCount(len(self.available_sessions))
        for row, s in enumerate(self.available_sessions):
            sid = s["id"]
            chk = QCheckBox()
            chk.setChecked(sid in self._checked_ids)
            chk.setStyleSheet("margin-left: 14px;")

            def _make_handler(session_id):
                return lambda checked: self._on_toggle(session_id, checked)

            chk.toggled.connect(_make_handler(sid))
            self.table.setCellWidget(row, 0, chk)

            item_id = QTableWidgetItem(str(sid))
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, item_id)

            item_name = QTableWidgetItem(s["name"])
            font = item_name.font()
            font.setBold(True)
            item_name.setFont(font)
            self.table.setItem(row, 2, item_name)

            v_left = s.get("videos_left", 15) if s.get("videos_left") is not None else 15
            item_vl = QTableWidgetItem(f"⚡ {v_left} Left")
            item_vl.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_vl.setForeground(QColor("#38bdf8") if v_left > 0 else QColor("#ef4444"))
            font_vl = item_vl.font()
            font_vl.setBold(True)
            item_vl.setFont(font_vl)
            self.table.setItem(row, 3, item_vl)

            item_st = QTableWidgetItem("AVAILABLE")
            item_st.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_st.setForeground(QColor("#10b981"))
            font_st = item_st.font()
            font_st.setBold(True)
            item_st.setFont(font_st)
            self.table.setItem(row, 4, item_st)

        layout.addWidget(self.table, stretch=1)

        # Bottom Action Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(34)
        btn_cancel.clicked.connect(self.reject)

        self.btn_confirm = QPushButton("🚀 Start Automation")
        self.btn_confirm.setObjectName("btn_success")
        self.btn_confirm.setFixedHeight(34)
        self.btn_confirm.setStyleSheet("font-weight: bold; padding: 0 20px; font-size: 12px;")
        self.btn_confirm.clicked.connect(self._on_confirm)

        btn_box.addWidget(btn_cancel)
        btn_box.addSpacing(10)
        btn_box.addWidget(self.btn_confirm)
        layout.addLayout(btn_box)

    def _update_capacity_display(self):
        sel_count = len(self._checked_ids)
        sat = min(sel_count, self.sessions_at_a_time) if sel_count > 0 else 1
        capacity = sel_count * self.videos_per_session
        self.lbl_selected_count.setText(f"{sel_count} session(s) selected")
        
        assigned_now = min(capacity, self.pending_prompts_count)
        self.btn_confirm.setText(f"🚀 Start Automation ({sel_count} Sessions · {assigned_now} Videos)")

        stats_text = (
            f"Selected Sessions: {sel_count}  |  Videos Per Session: {self.videos_per_session}  |  "
            f"Total Run Capacity: {capacity} ({sel_count} × {self.videos_per_session})  |  Pending Prompts: {self.pending_prompts_count}"
        )
        self.lbl_cap_stats.setText(stats_text)

        if self.pending_prompts_count > capacity:
            rem = self.pending_prompts_count - capacity
            self.lbl_cap_note.setText(
                f"ℹ️ {rem} prompt(s) will remain pending for the next available session cycle. "
                f"Automation will run {sel_count} sessions with {sat} rolling at a time."
            )
            self.lbl_cap_note.setStyleSheet("color: #f59e0b; font-size: 11px; font-weight: 500;")
        else:
            self.lbl_cap_note.setText(
                f"✓ All {self.pending_prompts_count} pending prompt(s) will be processed across {sel_count} session(s) "
                f"(running {sat} session(s) at a time in continuous rolling slots)."
            )
            self.lbl_cap_note.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 500;")

    def _on_toggle(self, sid: int, checked: bool):
        if checked:
            self._checked_ids.add(sid)
        else:
            self._checked_ids.discard(sid)
        self._update_capacity_display()

    def _select_all(self):
        for r in range(self.table.rowCount()):
            chk = self.table.cellWidget(r, 0)
            if chk:
                chk.setChecked(True)
        self._update_capacity_display()

    def _deselect_all(self):
        for r in range(self.table.rowCount()):
            chk = self.table.cellWidget(r, 0)
            if chk:
                chk.setChecked(False)
        self._update_capacity_display()

    def _on_confirm(self):
        if not self._checked_ids:
            QMessageBox.warning(self, "No Sessions Selected", "Please select at least one session to start automation.")
            return
        self.selected_sessions = [s for s in self.available_sessions if s["id"] in self._checked_ids]
        self.accept()

    def get_selected_sessions(self) -> list:
        return self.selected_sessions

class AutomationView(QWidget):
    def __init__(self, queue_manager: QueueManager, parent=None):
        super().__init__(parent)
        self.queue_manager = queue_manager
        self.config: AppConfig = db.load_app_config()
        self._init_ui()

        # Connect Admin Mode state listener for watermark settings visibility
        admin_manager.mode_changed.connect(self._on_admin_mode_changed)
        self._on_admin_mode_changed(admin_manager.is_admin)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_live_state)
        self.timer.start(1000)

    def showEvent(self, event):
        super().showEvent(event)
        self.config = db.load_app_config()
        if hasattr(self, "lbl_output_dir"):
            self.lbl_output_dir.setText(self.config.default_download_dir)
        self._refresh_live_state()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # ── 1. Header Title ──────────────────────────────────────────────────
        hdr_layout = QHBoxLayout()
        lbl_title = QLabel("Automation Center")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #f8fafc;")
        
        self.lbl_save_status = QLabel("✓ Settings saved")
        self.lbl_save_status.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 500;")

        hdr_layout.addWidget(lbl_title)
        hdr_layout.addStretch()
        hdr_layout.addWidget(self.lbl_save_status)
        main_layout.addLayout(hdr_layout)

        # ── 2. Settings & Main Controls Grid ─────────────────────────────────
        top_cards_layout = QHBoxLayout()
        top_cards_layout.setSpacing(16)

        # Card A: Automation Settings
        grp_settings = QGroupBox("Workflow Configuration")
        settings_layout = QVBoxLayout(grp_settings)
        settings_layout.setContentsMargins(16, 20, 16, 16)
        settings_layout.setSpacing(12)

        # Row 1: Model & Aspect Ratio (Locked to Seedance 2.5 & 9:16)
        row1 = QHBoxLayout()
        row1.setSpacing(12)

        lbl_model = QLabel("Video Model:")
        lbl_model.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        self.combo_model = QComboBox()
        self.combo_model.addItems(["Seedance 2.5"])
        self.combo_model.setCurrentIndex(0)
        self.combo_model.setEnabled(False)
        self.combo_model.setFixedWidth(140)
        self.combo_model.setToolTip("Locked to Seedance 2.5 for optimal video output.")
        self.combo_model.setStyleSheet("""
            QComboBox:disabled {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: bold;
            }
        """)

        lbl_ratio = QLabel("Aspect Ratio:")
        lbl_ratio.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        self.combo_ratio = QComboBox()
        self.combo_ratio.addItems(["9:16"])
        self.combo_ratio.setCurrentIndex(0)
        self.combo_ratio.setEnabled(False)
        self.combo_ratio.setFixedWidth(110)
        self.combo_ratio.setToolTip("Locked to 9:16 (Portrait format).")
        self.combo_ratio.setStyleSheet("""
            QComboBox:disabled {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: bold;
            }
        """)

        row1.addWidget(lbl_model)
        row1.addWidget(self.combo_model)
        row1.addSpacing(24)
        row1.addWidget(lbl_ratio)
        row1.addWidget(self.combo_ratio)
        row1.addStretch()
        settings_layout.addLayout(row1)

        # Row 2: Total Sessions To Run, Sessions At A Time, Videos Per Session
        row2 = QHBoxLayout()
        row2.setSpacing(12)

        lbl_tot = QLabel("Total Sessions To Run:")
        lbl_tot.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        self.spin_total_sessions = QSpinBox()
        self.spin_total_sessions.setRange(1, 100)
        self.spin_total_sessions.setValue(getattr(self.config, "total_sessions_to_run", 10))
        self.spin_total_sessions.setFixedWidth(70)
        self.spin_total_sessions.valueChanged.connect(self._save_settings)

        lbl_sat = QLabel("Sessions At A Time:")
        lbl_sat.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        self.spin_sat = QSpinBox()
        self.spin_sat.setRange(1, 50)
        self.spin_sat.setValue(self.config.sessions_at_a_time)
        self.spin_sat.setFixedWidth(70)
        self.spin_sat.valueChanged.connect(self._save_settings)

        lbl_vps = QLabel("Videos Per Session:")
        lbl_vps.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        self.spin_vps = QSpinBox()
        self.spin_vps.setRange(1, 15)
        self.spin_vps.setValue(self.config.videos_per_session)
        self.spin_vps.setFixedWidth(70)
        self.spin_vps.valueChanged.connect(self._save_settings)

        row2.addWidget(lbl_tot)
        row2.addWidget(self.spin_total_sessions)
        row2.addSpacing(18)
        row2.addWidget(lbl_sat)
        row2.addWidget(self.spin_sat)
        row2.addSpacing(18)
        row2.addWidget(lbl_vps)
        row2.addWidget(self.spin_vps)
        row2.addStretch()
        settings_layout.addLayout(row2)

        # Row 3: Watermark Remover (Admin Mode Only — hidden in User Mode)
        self.widget_watermark_row = QWidget()
        row3 = QHBoxLayout(self.widget_watermark_row)
        row3.setContentsMargins(0, 0, 0, 0)
        row3.setSpacing(12)

        self.chk_watermark = QCheckBox("Remove Watermark (Blur)")
        self.chk_watermark.setStyleSheet("font-weight: bold; color: #f8fafc;")
        self.chk_watermark.setChecked(getattr(self.config, "enable_watermark_remover", True))
        self.chk_watermark.toggled.connect(self._save_settings)

        lbl_blur = QLabel("Blur X:Y:W:H")
        lbl_blur.setStyleSheet("font-weight: 600; color: #cbd5e1;")

        self.spin_blur_x = QSpinBox()
        self.spin_blur_x.setRange(0, 3840)
        self.spin_blur_x.setValue(getattr(self.config, "blur_x", 540))
        self.spin_blur_x.valueChanged.connect(self._save_settings)

        self.spin_blur_y = QSpinBox()
        self.spin_blur_y.setRange(0, 2160)
        self.spin_blur_y.setValue(getattr(self.config, "blur_y", 1220))
        self.spin_blur_y.valueChanged.connect(self._save_settings)

        self.spin_blur_w = QSpinBox()
        self.spin_blur_w.setRange(1, 1000)
        self.spin_blur_w.setValue(getattr(self.config, "blur_w", 170))
        self.spin_blur_w.valueChanged.connect(self._save_settings)

        self.spin_blur_h = QSpinBox()
        self.spin_blur_h.setRange(1, 1000)
        self.spin_blur_h.setValue(getattr(self.config, "blur_h", 50))
        self.spin_blur_h.valueChanged.connect(self._save_settings)

        row3.addWidget(self.chk_watermark)
        row3.addSpacing(16)
        row3.addWidget(lbl_blur)
        row3.addWidget(self.spin_blur_x)
        row3.addWidget(self.spin_blur_y)
        row3.addWidget(self.spin_blur_w)
        row3.addWidget(self.spin_blur_h)
        row3.addStretch()
        settings_layout.addWidget(self.widget_watermark_row)

        # Dynamic Live Capacity Indicator
        self.lbl_capacity_indicator = QLabel()
        self.lbl_capacity_indicator.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 600;")
        settings_layout.addWidget(self.lbl_capacity_indicator)

        # Row 4: Output Storage Directory
        row4 = QHBoxLayout()
        row4.setSpacing(10)
        lbl_out = QLabel("Save Output To:")
        lbl_out.setStyleSheet("font-weight: 600; color: #cbd5e1;")

        self.lbl_output_dir = QLabel(self.config.default_download_dir)
        self.lbl_output_dir.setStyleSheet("color: #38bdf8; font-family: monospace; font-size: 11px; background: #0f172a; padding: 4px 8px; border-radius: 4px; border: 1px solid #1e293b;")

        btn_browse = QPushButton("📁 Browse...")
        btn_browse.setObjectName("btn_secondary")
        btn_browse.setFixedHeight(26)
        btn_browse.clicked.connect(self._change_output_dir)

        row4.addWidget(lbl_out)
        row4.addWidget(self.lbl_output_dir, stretch=1)
        row4.addWidget(btn_browse)
        settings_layout.addLayout(row4)

        # Recommendation helper text
        lbl_rec = QLabel("ℹ Continuous Rolling Pool: As each active session finishes its videos, the next session automatically starts in that slot.")
        lbl_rec.setStyleSheet("color: #94a3b8; font-size: 11px; font-style: italic;")
        settings_layout.addWidget(lbl_rec)

        top_cards_layout.addWidget(grp_settings, stretch=3)

        # Card B: Primary Control Buttons
        grp_controls = QGroupBox("Execution Controls")
        ctrl_layout = QVBoxLayout(grp_controls)
        ctrl_layout.setContentsMargins(16, 20, 16, 16)
        ctrl_layout.setSpacing(10)

        self.btn_start = QPushButton("▶  START AUTOMATION")
        self.btn_start.setObjectName("btn_success")
        self.btn_start.setFixedHeight(38)
        self.btn_start.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.btn_start.clicked.connect(self._on_start_automation)

        self.btn_stop = QPushButton("⏹  STOP AUTOMATION")
        self.btn_stop.setObjectName("btn_danger")
        self.btn_stop.setFixedHeight(34)
        self.btn_stop.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.btn_stop.clicked.connect(self._on_stop)

        btn_sub_row = QHBoxLayout()
        self.btn_reset_failed = QPushButton("🔄 Reset Failed")
        self.btn_reset_failed.setObjectName("btn_secondary")
        self.btn_reset_failed.clicked.connect(self._on_reset_failed)

        self.btn_clear_completed = QPushButton("🧹 Clear Completed")
        self.btn_clear_completed.setObjectName("btn_secondary")
        self.btn_clear_completed.clicked.connect(self._on_clear_completed)

        btn_sub_row.addWidget(self.btn_reset_failed)
        btn_sub_row.addWidget(self.btn_clear_completed)

        ctrl_layout.addWidget(self.btn_start)
        ctrl_layout.addWidget(self.btn_stop)
        ctrl_layout.addLayout(btn_sub_row)
        ctrl_layout.addStretch()

        top_cards_layout.addWidget(grp_controls, stretch=2)
        main_layout.addLayout(top_cards_layout)

        # ── 3. Live Active Sessions & Multi-Tab Progress Monitor ─────────────
        grp_monitor = QGroupBox("Active Session Instances & Tab Generations")
        mon_layout = QVBoxLayout(grp_monitor)
        mon_layout.setContentsMargins(12, 16, 12, 12)

        self.table_workers = QTableWidget()
        self.table_workers.setColumnCount(7)
        self.table_workers.setHorizontalHeaderLabels([
            "Slot #", "Assigned Session", "Stage / Status", "Active Tabs", "Videos Done", "Current Job", "Elapsed Time"
        ])
        self.table_workers.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_workers.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_workers.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        mon_layout.addWidget(self.table_workers)
        main_layout.addWidget(grp_monitor, stretch=1)

        self._save_settings()

    def _change_output_dir(self):
        fresh_config = db.load_app_config()
        new_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory", fresh_config.default_download_dir)
        if new_dir:
            fresh_config.default_download_dir = new_dir
            db.save_app_config(fresh_config)
            self.config = fresh_config
            if self.queue_manager:
                self.queue_manager.output_folder = new_dir
                self.queue_manager.config.default_download_dir = new_dir
            self.lbl_output_dir.setText(new_dir)
            QMessageBox.information(
                self,
                "Location Selected",
                f"📁 Output Download Location Selected:\n\n{new_dir}"
            )

    def _save_settings(self):
        """Persists automation settings directly into SQLite DB without overwriting download directory."""
        fresh_config = db.load_app_config()
        fresh_config.default_model = self.combo_model.currentText()
        fresh_config.default_ratio = self.combo_ratio.currentText()
        fresh_config.total_sessions_to_run = self.spin_total_sessions.value()
        fresh_config.videos_per_session = self.spin_vps.value()
        fresh_config.sessions_at_a_time = self.spin_sat.value()
        fresh_config.concurrency_limit = self.spin_sat.value()
        fresh_config.enable_watermark_remover = self.chk_watermark.isChecked()
        fresh_config.blur_x = self.spin_blur_x.value()
        fresh_config.blur_y = self.spin_blur_y.value()
        fresh_config.blur_w = self.spin_blur_w.value()
        fresh_config.blur_h = self.spin_blur_h.value()
        db.save_app_config(fresh_config)
        self.config = fresh_config
        if self.queue_manager:
            self.queue_manager.config = fresh_config
            self.queue_manager.output_folder = fresh_config.default_download_dir

        tot = self.spin_total_sessions.value()
        sat = self.spin_sat.value()
        vps = self.spin_vps.value()
        cap = tot * vps
        try:
            pending_cnt = db.get_pending_prompts_count()
        except Exception:
            pending_cnt = 0

        self.lbl_capacity_indicator.setText(
            f"📊 Selected Sessions: {tot}  |  Videos Per Session: {vps}  |  Total Run Capacity: {cap} ({tot} × {vps})  |  Pending Prompts: {pending_cnt}"
        )

        self.lbl_save_status.setText("✓ Settings saved")
        self.lbl_save_status.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 500;")

    def _on_start_automation(self):
        """Validates prerequisites, pops up available sessions selection dialog, and launches batch."""
        if not self.combo_model.currentText().strip():
            QMessageBox.warning(self, "Validation Failed", "Please select a Video Model before starting automation.")
            return

        if not self.combo_ratio.currentText().strip():
            QMessageBox.warning(self, "Validation Failed", "Please select an Aspect Ratio before starting automation.")
            return

        pending_prompts = db.get_pending_prompts()
        if not pending_prompts:
            QMessageBox.warning(self, "No Pending Prompts", "No pending prompts found in queue. Please add or import prompts in the Prompts tab.")
            return

        # Fetch only Available sessions
        all_sessions = db.get_all_sessions()
        available_sessions = [
            s for s in all_sessions
            if (s.get("status") or "Available").upper() in ("AVAILABLE", "IDLE", "RUNNING", "BUSY")
        ]

        if not available_sessions:
            QMessageBox.warning(self, "No Available Sessions", "No available sessions found in database. Please add sessions or restore expired sessions in the Sessions tab.")
            return

        # Show modal popup table of ONLY available sessions with dynamic capacity calculation
        tot_sess = self.spin_total_sessions.value()
        sat = self.spin_sat.value()
        vps = self.spin_vps.value()

        dlg = SessionSelectionDialog(
            available_sessions=available_sessions,
            target_total_sessions=tot_sess,
            sessions_at_a_time=sat,
            videos_per_session=vps,
            pending_prompts_count=len(pending_prompts),
            parent=self
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        selected_sessions = dlg.get_selected_sessions()
        if not selected_sessions:
            QMessageBox.warning(self, "No Sessions Selected", "Please select at least one available session.")
            return

        self._save_settings()

        capacity = len(selected_sessions) * vps
        assigned_count = min(len(pending_prompts), capacity)
        remaining_pending = len(pending_prompts) - assigned_count

        logger.info("==================================================", category="QUEUE")
        logger.info("🚀 START AUTOMATION CLICKED", category="QUEUE")
        logger.info(f"📊 Pending prompts in DB: {len(pending_prompts)}", category="QUEUE")
        logger.info(f"🔑 Total Selected sessions: {len(selected_sessions)}", category="QUEUE")
        logger.info(f"⚡ Sessions At A Time (Parallel Slots): {sat}", category="QUEUE")
        logger.info(f"📦 Videos Per Session: {vps}", category="QUEUE")
        logger.info(f"⚡ Total Run Capacity: {capacity} Videos ({len(selected_sessions)} sessions × {vps} VPS)", category="QUEUE")
        logger.info(f"🎬 Prompts assigned this run: {assigned_count} (Remaining pending: {remaining_pending})", category="QUEUE")
        logger.info("Calling QueueManager start...", category="QUEUE")

        try:
            run_id = self.queue_manager.prepare_and_start_automation(pending_prompts, selected_sessions)
            logger.info(f"🎉 Automation started (Run ID: {run_id})", category="QUEUE")
            logger.info(f"Worker created (Workers: {len(self.queue_manager.workers)})", category="QUEUE")
            logger.info("Browser launch requested", category="QUEUE")
            self._refresh_live_state()
            msg = (
                f"Automation launched successfully!\n\n"
                f"Run ID: {run_id}\n"
                f"Total Sessions: {len(selected_sessions)}\n"
                f"Parallel Slots: {min(sat, len(selected_sessions))}\n"
                f"Prompts Assigned: {assigned_count}\n"
                f"Remaining Pending: {remaining_pending}"
            )
            QMessageBox.information(self, "Automation Started", msg)
        except Exception as e:
            logger.error(f"❌ QueueManager start failed: {e}", category="QUEUE")
            QMessageBox.critical(self, "Launch Error", f"Failed to start automation: {e}")

    def _on_stop(self):
        reply = QMessageBox.question(self, "Stop Automation", "Are you sure you want to cleanly stop active automation?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.queue_manager.stop_automation()

    def _on_reset_failed(self):
        count = db.retry_failed_jobs()
        if count > 0:
            self.queue_manager.notify_status_change()
            self._refresh_live_state()
            QMessageBox.information(self, "Reset Complete", f"🔄 Successfully reset {count} failed job(s) to Pending status.")
        else:
            QMessageBox.information(self, "Notice", "There are currently no Failed jobs or prompts to reset.")

    def _on_clear_completed(self):
        count = db.clear_completed_prompts_and_jobs()
        if count > 0:
            self.queue_manager.notify_status_change()
            self._refresh_live_state()
            QMessageBox.information(self, "Cleaned", f"🧹 Successfully cleared {count} completed prompt(s) and jobs.")
        else:
            QMessageBox.information(self, "Notice", "There are currently no Completed prompts or jobs to clear.")

    def _refresh_live_state(self):
        """Updates live worker/session monitor table and capacity summary."""
        is_running = self.queue_manager._is_running
        self.btn_start.setEnabled(not is_running)

        tot = self.spin_total_sessions.value()
        vps = self.spin_vps.value()
        cap = tot * vps
        try:
            pending_cnt = db.get_pending_prompts_count()
        except Exception:
            pending_cnt = 0
        self.lbl_capacity_indicator.setText(
            f"📊 Selected Sessions: {tot}  |  Videos Per Session: {vps}  |  Total Run Capacity: {cap} ({tot} × {vps})  |  Pending Prompts: {pending_cnt}"
        )

        worker_states = self.queue_manager.get_live_worker_states()
        self.table_workers.setRowCount(len(worker_states))

        for row, w in enumerate(worker_states):
            self.table_workers.setItem(row, 0, QTableWidgetItem(f"Worker {w['worker_id']}"))
            self.table_workers.setItem(row, 1, QTableWidgetItem(w["session_name"]))
            
            stage_item = QTableWidgetItem(w["stage"])
            if "Completed" in w["stage"]:
                stage_item.setForeground(QColor("#10b981"))
            elif "Failed" in w["stage"] or "Error" in w["stage"]:
                stage_item.setForeground(QColor("#ef4444"))
            elif "Tab" in w["stage"] or "Monitoring" in w["stage"]:
                stage_item.setForeground(QColor("#3b82f6"))
            self.table_workers.setItem(row, 2, stage_item)

            self.table_workers.setItem(row, 3, QTableWidgetItem(f"{w.get('active_tabs', 0)} Active Tabs"))
            self.table_workers.setItem(row, 4, QTableWidgetItem(f"{w.get('videos_completed', 0)} Videos"))
            self.table_workers.setItem(row, 5, QTableWidgetItem(w["job_id"]))
            self.table_workers.setItem(row, 6, QTableWidgetItem(f"{w['elapsed_seconds']}s"))

    def _on_admin_mode_changed(self, is_admin: bool):
        """Toggles visibility of watermark remover coordinates controls (Admin Mode only)."""
        if hasattr(self, "widget_watermark_row"):
            self.widget_watermark_row.setVisible(is_admin)
