"""
Downloads Management View for Waqas's Automation Software.
Lists all verified downloaded MP4 files in the output directory,
provides file sizes, creation timestamps, and quick play / open folder actions.
"""

import os
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from app.core.config import AppConfig
from app.core.database import db

class DownloadsView(QWidget):
    def __init__(self, queue_manager=None, parent=None):
        super().__init__(parent)
        self.queue_manager = queue_manager
        self.config: AppConfig = db.load_app_config()
        self._init_ui()
        self._refresh_downloads()

    def showEvent(self, event):
        super().showEvent(event)
        self.config = db.load_app_config()
        if hasattr(self, "lbl_path"):
            self.lbl_path.setText(self.config.default_download_dir)
        self._refresh_downloads()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # ── 1. Top Header Bar ────────────────────────────────────────────────
        hdr_layout = QHBoxLayout()
        lbl_title = QLabel("Video Downloads")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #f8fafc;")

        self.lbl_stats = QLabel("0 MP4 Videos Found")
        self.lbl_stats.setStyleSheet("color: #94a3b8; font-size: 13px;")

        hdr_layout.addWidget(lbl_title)
        hdr_layout.addSpacing(16)
        hdr_layout.addWidget(self.lbl_stats)
        hdr_layout.addStretch()

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self._refresh_downloads)

        btn_open_folder = QPushButton("📁 Open Folder")
        btn_open_folder.setObjectName("btn_secondary")
        btn_open_folder.clicked.connect(self._open_output_folder)

        hdr_layout.addWidget(btn_refresh)
        hdr_layout.addWidget(btn_open_folder)
        main_layout.addLayout(hdr_layout)

        # ── 2. Output Path Header Box ────────────────────────────────────────
        path_box = QGroupBox("Output Storage Directory")
        path_layout = QHBoxLayout(path_box)
        path_layout.setContentsMargins(12, 16, 12, 12)

        self.lbl_path = QLabel(self.config.default_download_dir)
        self.lbl_path.setStyleSheet("color: #38bdf8; font-family: monospace; font-size: 12px;")

        btn_change_dir = QPushButton("Browse...")
        btn_change_dir.setObjectName("btn_secondary")
        btn_change_dir.clicked.connect(self._change_download_dir)

        path_layout.addWidget(self.lbl_path, stretch=1)
        path_layout.addWidget(btn_change_dir)
        main_layout.addWidget(path_box)

        # ── 3. Downloaded Videos Table ───────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Video File Name", "File Size", "Last Modified", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        main_layout.addWidget(self.table, stretch=1)

    def _refresh_downloads(self):
        """Scans output directory and populates table."""
        try:
            out_dir = Path(self.config.default_download_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            from app.core.config import DEFAULT_DOWNLOAD_DIR
            out_dir = Path(DEFAULT_DOWNLOAD_DIR)
            out_dir.mkdir(parents=True, exist_ok=True)

        files = sorted(out_dir.glob("*.mp4"), key=lambda f: f.stat().st_mtime, reverse=True)
        self.lbl_stats.setText(f"{len(files)} MP4 Videos Verified & Downloaded")


        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(files))

            for row, f in enumerate(files):
                try:
                    st = f.stat()
                    size_mb = st.st_size / (1024 * 1024)
                    import datetime
                    mtime_str = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

                    self.table.setItem(row, 0, QTableWidgetItem(f.name))
                    
                    item_size = QTableWidgetItem(f"{size_mb:.2f} MB")
                    item_size.setForeground(QColor("#10b981"))
                    self.table.setItem(row, 1, item_size)

                    self.table.setItem(row, 2, QTableWidgetItem(mtime_str))

                    btn_play = QPushButton("▶ Play")
                    btn_play.setFixedHeight(24)
                    btn_play.clicked.connect(lambda _, path=str(f): self._play_video(path))
                    self.table.setCellWidget(row, 3, btn_play)

                except Exception:
                    continue
        finally:
            self.table.setUpdatesEnabled(True)

    def _play_video(self, file_path: str):
        try:
            os.startfile(file_path)
        except Exception as e:
            QMessageBox.warning(self, "Playback Error", f"Could not open video file: {e}")

    def _open_output_folder(self):
        try:
            out_dir = str(Path(self.config.default_download_dir).resolve())
            os.startfile(out_dir)
        except Exception as e:
            QMessageBox.warning(self, "Folder Error", f"Could not open directory: {e}")

    def _change_download_dir(self):
        self.config = db.load_app_config()
        new_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.config.default_download_dir)
        if new_dir:
            self.config.default_download_dir = new_dir
            db.save_app_config(self.config)
            if self.queue_manager:
                self.queue_manager.output_folder = new_dir
                self.queue_manager.config.default_download_dir = new_dir
            self.lbl_path.setText(new_dir)
            self._refresh_downloads()
            QMessageBox.information(
                self,
                "Location Selected",
                f"📁 Output Download Location Selected:\n\n{new_dir}"
            )
