"""
Queue View for displaying live batch job statuses and execution logs.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor
from app.core.database import db

class QueueView(QWidget):
    def __init__(self, queue_manager, parent=None):
        super().__init__(parent)
        self.queue_manager = queue_manager
        self._init_ui()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_queue)
        self.timer.start(2000)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        header_layout = QHBoxLayout()
        lbl_title = QLabel("JOB QUEUE & STATUS MONITOR")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00f0ff;")
        
        btn_retry_failed = QPushButton("🔁 Retry Failed")
        btn_retry_failed.setObjectName("btn_warning")
        btn_retry_failed.clicked.connect(self._on_retry_failed_click)

        btn_clear_queue = QPushButton("🧹 Clear Queue")
        btn_clear_queue.setObjectName("btn_clear")
        btn_clear_queue.clicked.connect(self._on_clear_queue_click)

        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(btn_retry_failed)
        header_layout.addWidget(btn_clear_queue)

        main_layout.addLayout(header_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Job ID", "Prompt Snippet", "Session", "Worker", "Status", "Failure Reason", "Downloaded File", "Completed At"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        main_layout.addWidget(self.table)

    def _on_retry_failed_click(self):
        count = db.retry_failed_jobs()
        if count > 0:
            QMessageBox.information(
                self,
                "Retry Triggered",
                f"🔁 {count} failed job(s) reset to Pending status using their original assigned session(s)!"
            )
            self.refresh_queue()
        else:
            QMessageBox.information(self, "No Failed Jobs", "There are currently no failed jobs in the queue to retry.")

    def _on_clear_queue_click(self):
        reply = QMessageBox.question(
            self,
            "Clear Job Queue",
            "Are you sure you want to clear all jobs from the queue and reset dashboard metrics?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.queue_manager.clear_queue_and_dashboard()
            self.refresh_queue()
            QMessageBox.information(self, "Queue Cleared", "The Job Queue and status monitor have been cleared successfully.")

    def refresh_queue(self):
        if not self.isVisible():
            return
        jobs = db.get_all_jobs()
        if not jobs:
            self.table.setRowCount(0)
            return

        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(jobs))
            for row, j in enumerate(jobs):
                self.table.setItem(row, 0, QTableWidgetItem(j["id"]))
                self.table.setItem(row, 1, QTableWidgetItem(j.get("prompt_text") or "-"))
                self.table.setItem(row, 2, QTableWidgetItem(j.get("session_name") or "-"))
                
                w_str = f"Worker {j['worker_id']:02d}" if j.get("worker_id") else "-"
                self.table.setItem(row, 3, QTableWidgetItem(w_str))
                
                status_item = QTableWidgetItem(j.get("status") or "Pending")
                if j.get("status") == "Failed":
                    status_item.setForeground(QColor("#ef4444"))
                elif j.get("status") == "Completed":
                    status_item.setForeground(QColor("#22c55e"))
                self.table.setItem(row, 4, status_item)

                # Failure Reason Column (Error message / Stage at failure)
                err_msg = j.get("error_message") or j.get("stage_at_failure") or "-"
                err_item = QTableWidgetItem(err_msg)
                if j.get("status") == "Failed":
                    err_item.setForeground(QColor("#f87171"))
                self.table.setItem(row, 5, err_item)

                self.table.setItem(row, 6, QTableWidgetItem(j.get("downloaded_filename") or "-"))
                self.table.setItem(row, 7, QTableWidgetItem(j.get("completed_at") or "-"))
        finally:
            self.table.setUpdatesEnabled(True)
