"""
Settings View for App Configuration, Extension Path, Download Folder & Concurrency Limit.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox, QPushButton, QFileDialog, QGroupBox, QMessageBox
)
from app.core.database import db
from app.core.config import AppConfig

class SettingsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = db.load_app_config()
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        lbl_title = QLabel("SETTINGS & PREFERENCES")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #f8fafc;")
        main_layout.addWidget(lbl_title)

        # Automation Settings Group
        box_auto = QGroupBox("AUTOMATION & CONCURRENCY")
        l_auto = QVBoxLayout(box_auto)

        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Max Concurrent Workers (Default: 5):"))
        self.spn_concurrency = QSpinBox()
        self.spn_concurrency.setRange(1, 20)
        self.spn_concurrency.setValue(self.config.concurrency_limit)
        r1.addWidget(self.spn_concurrency)
        r1.addStretch()
        l_auto.addLayout(r1)

        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Generation Timeout (Seconds):"))
        self.spn_gen_timeout = QSpinBox()
        self.spn_gen_timeout.setRange(30, 3600)
        self.spn_gen_timeout.setValue(self.config.generation_timeout_sec)
        r2.addWidget(self.spn_gen_timeout)
        r2.addStretch()
        l_auto.addLayout(r2)

        main_layout.addWidget(box_auto)

        # Storage & Extension Settings Group
        box_paths = QGroupBox("DOWNLOADS & EXTENSION DEPENDENCY")
        l_paths = QVBoxLayout(box_paths)

        pr1 = QHBoxLayout()
        pr1.addWidget(QLabel("Extension Path:"))
        self.txt_ext_path = QLineEdit(self.config.extension_path)
        btn_ext_browse = QPushButton("Browse...")
        btn_ext_browse.setObjectName("btn_secondary")
        btn_ext_browse.clicked.connect(self._on_browse_ext)
        pr1.addWidget(self.txt_ext_path)
        pr1.addWidget(btn_ext_browse)
        l_paths.addLayout(pr1)

        pr2 = QHBoxLayout()
        pr2.addWidget(QLabel("Output / Download Folder:"))
        self.txt_dl_path = QLineEdit(self.config.default_download_dir)
        btn_dl_browse = QPushButton("Browse...")
        btn_dl_browse.setObjectName("btn_secondary")
        btn_dl_browse.clicked.connect(self._on_browse_dl)
        
        btn_dl_open = QPushButton("Open Folder")
        btn_dl_open.setObjectName("btn_secondary")
        btn_dl_open.clicked.connect(self._on_open_dl)

        pr2.addWidget(self.txt_dl_path)
        pr2.addWidget(btn_dl_browse)
        pr2.addWidget(btn_dl_open)
        l_paths.addLayout(pr2)

        main_layout.addWidget(box_paths)

        # Save Button
        btn_save = QPushButton("💾 SAVE SETTINGS")
        btn_save.setObjectName("btn_success")
        btn_save.clicked.connect(self._on_save)
        main_layout.addWidget(btn_save)
        main_layout.addStretch()

    def _on_browse_ext(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Extension Folder", self.txt_ext_path.text())
        if folder:
            self.txt_ext_path.setText(folder)

    def _on_browse_dl(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Default Download Directory", self.txt_dl_path.text())
        if folder:
            self.txt_dl_path.setText(folder)
            self.config.default_download_dir = folder
            db.save_app_config(self.config)
            QMessageBox.information(
                self,
                "Location Selected",
                f"📁 Output Download Location Selected:\n\n{folder}"
            )

    def _on_open_dl(self):
        import os
        path = self.txt_dl_path.text().strip()
        if os.path.exists(path):
            os.startfile(path)
        else:
            QMessageBox.warning(self, "Warning", f"Directory does not exist yet: {path}")

    def _on_save(self):
        self.config.concurrency_limit = self.spn_concurrency.value()
        self.config.generation_timeout_sec = self.spn_gen_timeout.value()
        self.config.extension_path = self.txt_ext_path.text().strip()
        self.config.default_download_dir = self.txt_dl_path.text().strip()

        db.save_app_config(self.config)
        QMessageBox.information(self, "Success", "Settings saved successfully!")
