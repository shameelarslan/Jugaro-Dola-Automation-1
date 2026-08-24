"""
Professional Dashboard View for Waqas's Automation Software.
Displays overview KPI cards, live automation status badge, progress bar,
active session/tab progress monitors, and real-time activity log feed.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QFrame
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor, QFont

import collections
from app.gui.components.stat_card import StatCard
from app.core.queue_manager import QueueManager
from app.core.database import db
from app.core.logger import logger, LogEntry
from app.core.admin_manager import admin_manager

class DashboardView(QWidget):
    def __init__(self, queue_manager: QueueManager, parent=None):
        super().__init__(parent)
        self.queue_manager = queue_manager
        self._log_queue = collections.deque(maxlen=1000)
        self._all_history = collections.deque(maxlen=1000)
        self._auto_scroll_enabled = True
        self._is_programmatic_scroll = False
        self._init_ui()

        # Connect logger callback for real-time live log box
        logger.register_callback(self._on_new_log)

        # Connect Admin Mode state listener
        admin_manager.mode_changed.connect(self._on_mode_changed)

        # 1-second UI refresh timer for stats
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_dashboard)
        self.timer.start(1000)

        # Smooth 250ms UI timer to safely drain logs onto the GUI thread
        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self._drain_logs)
        self.log_timer.start(250)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_dashboard()
        self._drain_logs()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # ── 1. Top Header & Automation Status ────────────────────────────────
        status_card = QFrame()
        status_card.setObjectName("card")
        status_card_layout = QHBoxLayout(status_card)
        status_card_layout.setContentsMargins(16, 10, 16, 10)

        lbl_dash_title = QLabel("System Dashboard")
        lbl_dash_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #f8fafc;")

        btn_clear_dash = QPushButton("🧹 Clear Dashboard")
        btn_clear_dash.setObjectName("btn_secondary")
        btn_clear_dash.clicked.connect(self._on_clear_dashboard)

        status_card_layout.addWidget(lbl_dash_title)
        status_card_layout.addSpacing(16)
        status_card_layout.addWidget(btn_clear_dash)
        status_card_layout.addStretch()

        # Shifted Total Videos Generated Badge (Where the red arrow points)
        self.badge_lifetime = QFrame()
        self.badge_lifetime.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #172554, stop:1 #1e3a8a);
                border: 1px solid #3b82f6;
                border-radius: 8px;
                padding: 2px 14px;
            }
        """)
        lifetime_layout = QHBoxLayout(self.badge_lifetime)
        lifetime_layout.setContentsMargins(10, 4, 10, 4)
        lifetime_layout.setSpacing(10)

        lbl_life_icon = QLabel("🎬 TOTAL VID GEN:")
        lbl_life_icon.setStyleSheet("color: #93c5fd; font-weight: 800; font-size: 12px; border: none; background: transparent;")

        self.lbl_lifetime_val = QLabel("0")
        self.lbl_lifetime_val.setStyleSheet("color: #facc15; font-weight: 900; font-size: 16px; border: none; background: transparent;")

        lifetime_layout.addWidget(lbl_life_icon)
        lifetime_layout.addWidget(self.lbl_lifetime_val)

        status_card_layout.addWidget(self.badge_lifetime)
        status_card_layout.addSpacing(20)

        lbl_status_prefix = QLabel("Status:")
        lbl_status_prefix.setStyleSheet("color: #94a3b8; font-weight: 600; font-size: 13px;")
        
        self.lbl_status_badge = QLabel("IDLE")
        self.lbl_status_badge.setStyleSheet("""
            background-color: #334155;
            color: #94a3b8;
            font-weight: bold;
            font-size: 12px;
            padding: 4px 12px;
            border-radius: 12px;
        """)

        status_card_layout.addWidget(lbl_status_prefix)
        status_card_layout.addWidget(self.lbl_status_badge)
        main_layout.addWidget(status_card)

        # ── 2. KPI Overview Metric Cards ─────────────────────────────────────
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(12)

        self.card_total = StatCard("TOTAL PROMPTS", "0", "#3b82f6")
        self.card_pending = StatCard("PENDING", "0", "#94a3b8")
        self.card_running = StatCard("RUNNING", "0", "#f59e0b")
        self.card_completed = StatCard("COMPLETED", "0", "#10b981")
        self.card_failed = StatCard("FAILED", "0", "#ef4444")
        self.card_sessions = StatCard("ACTIVE SESSIONS", "0", "#8b5cf6")
        self.card_downloads = StatCard("DOWNLOADED", "0", "#06b6d4")

        kpi_layout.addWidget(self.card_total)
        kpi_layout.addWidget(self.card_pending)
        kpi_layout.addWidget(self.card_running)
        kpi_layout.addWidget(self.card_completed)
        kpi_layout.addWidget(self.card_failed)
        kpi_layout.addWidget(self.card_sessions)
        kpi_layout.addWidget(self.card_downloads)
        main_layout.addLayout(kpi_layout)

        # ── 3. Progress Section ──────────────────────────────────────────────
        prog_card = QFrame()
        prog_card.setObjectName("card")
        prog_layout = QVBoxLayout(prog_card)
        prog_layout.setContentsMargins(16, 12, 16, 12)
        prog_layout.setSpacing(8)

        prog_hdr = QHBoxLayout()
        self.lbl_progress_text = QLabel("0 / 0 videos completed (0%)")
        self.lbl_progress_text.setStyleSheet("font-weight: 600; color: #f8fafc; font-size: 13px;")
        prog_hdr.addWidget(self.lbl_progress_text)
        prog_hdr.addStretch()
        prog_layout.addLayout(prog_hdr)

        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        prog_layout.addWidget(self.prog_bar)

        main_layout.addWidget(prog_card)

        # ── 4. Split Grid: Live Active Sessions & Recent Activity Logs ───────
        bottom_grid = QHBoxLayout()
        bottom_grid.setSpacing(16)

        # Left: Live Active Sessions Table
        grp_sessions = QGroupBox("Active Browser Sessions & Multi-Tab Status")
        sess_layout = QVBoxLayout(grp_sessions)
        sess_layout.setContentsMargins(10, 16, 10, 10)

        self.table_sessions = QTableWidget()
        self.table_sessions.setColumnCount(5)
        self.table_sessions.setHorizontalHeaderLabels(["Worker", "Session", "Stage", "Active Tabs", "Elapsed"])
        self.table_sessions.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_sessions.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        sess_layout.addWidget(self.table_sessions)
        bottom_grid.addWidget(grp_sessions, stretch=3)

        # Right: Live Activity Stream
        grp_logs = QGroupBox("Recent Live Activity Feed")
        logs_layout = QVBoxLayout(grp_logs)
        logs_layout.setContentsMargins(10, 14, 10, 10)

        # Activity Header with Auto-scroll Indicator and Quick Clear Button
        logs_hdr = QHBoxLayout()
        self.lbl_autoscroll_status = QLabel("● Auto-scroll: ON")
        self.lbl_autoscroll_status.setStyleSheet("color: #10b981; font-size: 10px; font-weight: bold;")
        
        btn_clear_logs = QPushButton("🗑 Clear Logs")
        btn_clear_logs.setObjectName("btn_secondary")
        btn_clear_logs.setStyleSheet("padding: 2px 8px; font-size: 10px;")
        btn_clear_logs.clicked.connect(self._on_clear_logs_only)

        logs_hdr.addStretch()
        logs_hdr.addWidget(self.lbl_autoscroll_status)
        logs_hdr.addSpacing(8)
        logs_hdr.addWidget(btn_clear_logs)
        logs_layout.addLayout(logs_hdr)

        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setStyleSheet("""
            background-color: #0b0f19;
            color: #94a3b8;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 11px;
            border: 1px solid #1e293b;
            border-radius: 6px;
        """)
        self.txt_logs.verticalScrollBar().valueChanged.connect(self._on_log_scroll_changed)

        logs_layout.addWidget(self.txt_logs)
        bottom_grid.addWidget(grp_logs, stretch=2)

        main_layout.addLayout(bottom_grid, stretch=1)

    def _on_clear_logs_only(self):
        """Clears only the live log box."""
        self._log_queue.clear()
        self.txt_logs.clear()

    def _on_clear_dashboard(self):
        """Clears all dashboard metrics, job history, active tables, and live logs while keeping Total Vid Gen intact."""
        reply = QMessageBox.question(
            self, "Clear Dashboard",
            "Are you sure you want to clear the dashboard metrics, job history, and live activity feed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.queue_manager.clear_queue_and_dashboard()
        self._log_queue.clear()
        self.txt_logs.clear()
        self.table_sessions.setRowCount(0)
        self.card_total.set_value("0")
        self.card_pending.set_value("0")
        self.card_running.set_value("0")
        self.card_completed.set_value("0")
        self.card_failed.set_value("0")
        self.card_sessions.set_value("0")
        self.card_downloads.set_value("0")
        self.prog_bar.setValue(0)
        self.lbl_progress_text.setText("0 / 0 videos completed (0%)")
        self.lbl_status_badge.setText("IDLE")
        self.lbl_status_badge.setStyleSheet("background-color: #334155; color: #94a3b8; font-weight: bold; padding: 4px 12px; border-radius: 12px;")

        # Total Vid Gen stays persistent in top header
        lifetime_total = db.get_lifetime_videos_count()
        self.lbl_lifetime_val.setText(str(lifetime_total))
        QMessageBox.information(self, "Dashboard Cleared", "Dashboard metrics and history have been cleared successfully.")

    def showEvent(self, event):
        """When switching back to Dashboard tab, automatically re-enable auto-scroll and jump to latest."""
        super().showEvent(event)
        self._auto_scroll_enabled = True
        self.lbl_autoscroll_status.setText("● Auto-scroll: ON")
        self.lbl_autoscroll_status.setStyleSheet("color: #10b981; font-size: 10px; font-weight: bold;")
        self._is_programmatic_scroll = True
        scrollbar = self.txt_logs.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        self._is_programmatic_scroll = False

    def _on_log_scroll_changed(self, value: int):
        """Pauses auto-scroll if user manually scrolls up; resumes if user reaches bottom."""
        if self._is_programmatic_scroll:
            return
        scrollbar = self.txt_logs.verticalScrollBar()
        max_val = scrollbar.maximum()
        if value < max_val - 25:
            if self._auto_scroll_enabled:
                self._auto_scroll_enabled = False
                self.lbl_autoscroll_status.setText("○ Auto-scroll: PAUSED (scroll to bottom or switch tab to resume)")
                self.lbl_autoscroll_status.setStyleSheet("color: #f59e0b; font-size: 10px; font-weight: bold;")
        else:
            if not self._auto_scroll_enabled:
                self._auto_scroll_enabled = True
                self.lbl_autoscroll_status.setText("● Auto-scroll: ON")
                self.lbl_autoscroll_status.setStyleSheet("color: #10b981; font-size: 10px; font-weight: bold;")

    def _on_new_log(self, entry: LogEntry):
        """Thread-safe log receiver: appends to deque from any thread."""
        self._log_queue.append(entry)
        self._all_history.append(entry)

    def _on_mode_changed(self, is_admin: bool):
        """Re-renders Live Activity Feed according to User vs Admin mode."""
        self.txt_logs.clear()
        lines = []
        for entry in self._all_history:
            formatted = admin_manager.format_log_entry(entry, is_admin=is_admin)
            if not formatted:
                continue
            color = "#94a3b8"
            if entry.level == "ERROR":
                color = "#ef4444"
            elif entry.level in ("WARN", "WARNING"):
                color = "#f59e0b"
            elif entry.level == "INFO":
                color = "#38bdf8"

            lines.append(f"<span style='color:{color};'>{formatted}</span>")

        if lines:
            self.txt_logs.setHtml("<br>".join(lines[-400:]))
            self._is_programmatic_scroll = True
            scrollbar = self.txt_logs.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            self._is_programmatic_scroll = False

    def _drain_logs(self):
        """Drains the log queue strictly on the Qt main GUI thread with high performance batch appending."""
        if not self._log_queue:
            return

        is_admin = admin_manager.is_admin
        batch_lines = []
        count = 0
        while self._log_queue and count < 100:
            count += 1
            try:
                entry = self._log_queue.popleft()
                formatted = admin_manager.format_log_entry(entry, is_admin=is_admin)
                if not formatted:
                    continue

                color = "#94a3b8"
                if entry.level == "ERROR":
                    color = "#ef4444"
                elif entry.level in ("WARN", "WARNING"):
                    color = "#f59e0b"
                elif entry.level == "INFO":
                    color = "#38bdf8"

                batch_lines.append(f"<span style='color:{color};'>{formatted}</span>")
            except IndexError:
                break

        if batch_lines:
            # Memory safety: keep document under 800 blocks to prevent memory ballooning
            doc = self.txt_logs.document()
            if doc.blockCount() > 800:
                cursor = self.txt_logs.textCursor()
                cursor.movePosition(cursor.MoveOperation.Start)
                cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor, 200)
                cursor.removeSelectedText()

            # Batch append
            self.txt_logs.append("<br>".join(batch_lines))

            if self._auto_scroll_enabled:
                self._is_programmatic_scroll = True
                scrollbar = self.txt_logs.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
                self._is_programmatic_scroll = False

    def _refresh_dashboard(self):
        """Updates metric cards, progress bar, and session status."""
        if not self.isVisible():
            return

        stats = self.queue_manager.get_batch_summary_stats()
        total = stats.get("total", 0)
        completed = stats.get("completed", 0)
        failed = stats.get("failed", 0)
        running = stats.get("running", 0)
        pending = stats.get("pending", 0)
        active_sess = stats.get("active_sessions", 0)

        self.lbl_lifetime_val.setText(str(db.get_lifetime_videos_count()))
        self.card_total.set_value(str(total))
        self.card_pending.set_value(str(pending))
        self.card_running.set_value(str(running))
        self.card_completed.set_value(str(completed))
        self.card_failed.set_value(str(failed))
        self.card_sessions.set_value(str(active_sess))
        self.card_downloads.set_value(str(completed))

        # Progress bar
        if total > 0:
            pct = int((completed / total) * 100)
            self.prog_bar.setValue(pct)
            self.lbl_progress_text.setText(f"{completed} / {total} videos completed ({pct}%)")
        else:
            self.prog_bar.setValue(0)
            self.lbl_progress_text.setText("0 / 0 videos completed (0%)")

        # Automation Status Badge
        if self.queue_manager._stop_requested:
            self.lbl_status_badge.setText("STOPPED")
            self.lbl_status_badge.setStyleSheet("background-color: #7f1d1d; color: #fca5a5; font-weight: bold; padding: 4px 12px; border-radius: 12px;")
        elif self.queue_manager._is_running:
            if self.queue_manager._is_paused:
                self.lbl_status_badge.setText("PAUSED")
                self.lbl_status_badge.setStyleSheet("background-color: #78350f; color: #fde68a; font-weight: bold; padding: 4px 12px; border-radius: 12px;")
            else:
                self.lbl_status_badge.setText("RUNNING")
                self.lbl_status_badge.setStyleSheet("background-color: #14532d; color: #86efac; font-weight: bold; padding: 4px 12px; border-radius: 12px;")
        elif completed > 0 and pending == 0 and running == 0:
            self.lbl_status_badge.setText("COMPLETED")
            self.lbl_status_badge.setStyleSheet("background-color: #1e3a8a; color: #93c5fd; font-weight: bold; padding: 4px 12px; border-radius: 12px;")
        elif failed > 0 and running == 0:
            self.lbl_status_badge.setText("ERROR")
            self.lbl_status_badge.setStyleSheet("background-color: #7f1d1d; color: #fca5a5; font-weight: bold; padding: 4px 12px; border-radius: 12px;")
        else:
            self.lbl_status_badge.setText("IDLE")
            self.lbl_status_badge.setStyleSheet("background-color: #334155; color: #94a3b8; font-weight: bold; padding: 4px 12px; border-radius: 12px;")

        # Active Session Instances Table
        worker_states = self.queue_manager.get_live_worker_states()
        self.table_sessions.setRowCount(len(worker_states))
        for r, w in enumerate(worker_states):
            self.table_sessions.setItem(r, 0, QTableWidgetItem(f"Worker {w['worker_id']}"))
            self.table_sessions.setItem(r, 1, QTableWidgetItem(w["session_name"]))
            
            stage_item = QTableWidgetItem(w["stage"])
            if "Expired" in w["stage"] or "Login" in w["stage"]:
                stage_item.setForeground(QColor("#ef4444"))
                stage_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            elif "Completed" in w["stage"]:
                stage_item.setForeground(QColor("#10b981"))
            elif "Failed" in w["stage"] or "Error" in w["stage"]:
                stage_item.setForeground(QColor("#ef4444"))
            elif "Tab" in w["stage"] or "Monitoring" in w["stage"]:
                stage_item.setForeground(QColor("#3b82f6"))
            self.table_sessions.setItem(r, 2, stage_item)

            self.table_sessions.setItem(r, 3, QTableWidgetItem(f"{w.get('active_tabs', 0)} Tabs"))
            self.table_sessions.setItem(r, 4, QTableWidgetItem(f"{w['elapsed_seconds']}s"))
