"""
Logs View for Color-Coded Real-Time Log Streaming & Export.
"""

import collections
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QFileDialog, QFrame
)
from PyQt6.QtCore import QTimer
from app.core.logger import logger, LogEntry
from app.core.admin_manager import admin_manager

class LogsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._log_queue = collections.deque(maxlen=2000)
        self._all_history = collections.deque(maxlen=2000)
        self._auto_scroll_enabled = True
        self._is_programmatic_scroll = False
        self._init_ui()

        # Connect logger callback for real-time live log stream
        logger.register_callback(self._on_log_entry)

        # Connect Admin Mode state listener
        admin_manager.mode_changed.connect(self._on_mode_changed)

        # Smooth 250ms UI timer to safely drain logs onto the GUI thread
        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self._drain_logs)
        self.log_timer.start(250)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        hdr_row = QHBoxLayout()
        lbl_title = QLabel("SYSTEM & WORKER APPLICATION LOGS")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #f8fafc;")

        self.lbl_mode_badge = QLabel("👤 User Mode (Filtered)")
        self.lbl_mode_badge.setStyleSheet("""
            background-color: #1e293b;
            color: #94a3b8;
            font-size: 11px;
            font-weight: bold;
            padding: 4px 10px;
            border-radius: 6px;
            border: 1px solid #334155;
        """)

        self.lbl_autoscroll_status = QLabel("● Auto-scroll: ON")
        self.lbl_autoscroll_status.setStyleSheet("color: #10b981; font-size: 11px; font-weight: bold; padding: 4px 8px; background-color: #0f172a; border-radius: 4px; border: 1px solid #1e293b;")

        btn_clear = QPushButton("🗑 Clear Console")
        btn_clear.setObjectName("btn_secondary")
        btn_clear.clicked.connect(self._on_clear)

        btn_export = QPushButton("💾 Export Logs")
        btn_export.setObjectName("btn_secondary")
        btn_export.clicked.connect(self._on_export)

        hdr_row.addWidget(lbl_title)
        hdr_row.addSpacing(10)
        hdr_row.addWidget(self.lbl_mode_badge)
        hdr_row.addStretch()
        hdr_row.addWidget(self.lbl_autoscroll_status)
        hdr_row.addWidget(btn_clear)
        hdr_row.addWidget(btn_export)

        main_layout.addLayout(hdr_row)

        self.txt_console = QTextEdit()
        self.txt_console.setReadOnly(True)
        self.txt_console.setStyleSheet("""
            QTextEdit {
                background-color: #020617;
                color: #e2e8f0;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        self.txt_console.verticalScrollBar().valueChanged.connect(self._on_log_scroll_changed)
        main_layout.addWidget(self.txt_console)

    def showEvent(self, event):
        """When switching back to Activity / Logs tab, automatically re-enable auto-scroll and jump to latest."""
        super().showEvent(event)
        self._auto_scroll_enabled = True
        self.lbl_autoscroll_status.setText("● Auto-scroll: ON")
        self.lbl_autoscroll_status.setStyleSheet("color: #10b981; font-size: 11px; font-weight: bold; padding: 4px 8px; background-color: #0f172a; border-radius: 4px; border: 1px solid #1e293b;")
        self._is_programmatic_scroll = True
        scrollbar = self.txt_console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        self._is_programmatic_scroll = False

    def _on_log_scroll_changed(self, value: int):
        """Pauses auto-scroll if user manually scrolls up; resumes if user reaches bottom."""
        if self._is_programmatic_scroll:
            return
        scrollbar = self.txt_console.verticalScrollBar()
        max_val = scrollbar.maximum()
        if value < max_val - 25:
            if self._auto_scroll_enabled:
                self._auto_scroll_enabled = False
                self.lbl_autoscroll_status.setText("○ Auto-scroll: PAUSED (scroll to bottom or switch tab to resume)")
                self.lbl_autoscroll_status.setStyleSheet("color: #f59e0b; font-size: 11px; font-weight: bold; padding: 4px 8px; background-color: #0f172a; border-radius: 4px; border: 1px solid #1e293b;")
        else:
            if not self._auto_scroll_enabled:
                self._auto_scroll_enabled = True
                self.lbl_autoscroll_status.setText("● Auto-scroll: ON")
                self.lbl_autoscroll_status.setStyleSheet("color: #10b981; font-size: 11px; font-weight: bold; padding: 4px 8px; background-color: #0f172a; border-radius: 4px; border: 1px solid #1e293b;")

    def _on_log_entry(self, entry: LogEntry):
        """Thread-safe log receiver: appends to deque from any thread."""
        self._log_queue.append(entry)
        self._all_history.append(entry)

    def _on_mode_changed(self, is_admin: bool):
        """Re-renders existing console logs according to mode permissions."""
        if is_admin:
            self.lbl_mode_badge.setText("👑 Admin Mode (Full Telemetry)")
            self.lbl_mode_badge.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #854d0e, stop:1 #ca8a04);
                color: #ffffff;
                font-size: 11px;
                font-weight: 800;
                padding: 4px 10px;
                border-radius: 6px;
                border: 1px solid #facc15;
            """)
        else:
            self.lbl_mode_badge.setText("👤 User Mode (Filtered)")
            self.lbl_mode_badge.setStyleSheet("""
                background-color: #1e293b;
                color: #94a3b8;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 10px;
                border-radius: 6px;
                border: 1px solid #334155;
            """)

        # Re-render console with filtered / full history
        self.txt_console.clear()
        lines = []
        for entry in self._all_history:
            formatted = admin_manager.format_log_entry(entry, is_admin=is_admin)
            if not formatted:
                continue
            color = "#e2e8f0"
            if entry.level == "ERROR":
                color = "#ef4444"
            elif entry.level in ("WARN", "WARNING"):
                color = "#f59e0b"
            elif entry.level == "INFO":
                color = "#38bdf8"
            lines.append(f"<span style='color: {color};'>{formatted}</span>")

        if lines:
            self.txt_console.setHtml("<br>".join(lines[-800:]))
            self._is_programmatic_scroll = True
            scrollbar = self.txt_console.verticalScrollBar()
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

                color = "#e2e8f0"
                if entry.level == "ERROR":
                    color = "#ef4444"
                elif entry.level in ("WARN", "WARNING"):
                    color = "#f59e0b"
                elif entry.level == "INFO":
                    color = "#38bdf8"
                    
                html = f"<span style='color: {color};'>{formatted}</span>"
                batch_lines.append(html)
            except IndexError:
                break

        if batch_lines:
            doc = self.txt_console.document()
            if doc.blockCount() > 1000:
                cursor = self.txt_console.textCursor()
                cursor.movePosition(cursor.MoveOperation.Start)
                cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor, 250)
                cursor.removeSelectedText()

            self.txt_console.append("<br>".join(batch_lines))

            if self._auto_scroll_enabled:
                self._is_programmatic_scroll = True
                scrollbar = self.txt_console.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
                self._is_programmatic_scroll = False

    def _on_clear(self):
        self.txt_console.clear()

    def _on_export(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Log File", "dola_logs.txt", "Text Files (*.txt)")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.txt_console.toPlainText())
