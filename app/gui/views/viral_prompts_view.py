"""
Viral Prompts Library View for Waqas Automation Pro.
Displays 200+ HTML-based viral video prompts with instant search, category filtering,
clean uncorrupted text display, one-click clipboard copying, and SQLite database import.
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QListWidget, QListWidgetItem, QTextEdit, QFrame,
    QSplitter, QMessageBox, QFileDialog, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
from app.managers.viral_prompt_manager import viral_prompt_manager
from app.utils.logger import logger

class ViralPromptsView(QWidget):
    """
    Rich interactive view for browsing, filtering, copying, and importing 200+ viral prompts.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_selected_prompt = None
        self._init_ui()
        self._load_prompts_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(14)

        # ── Top Header Bar ───────────────────────────────────────────────────
        hdr_frame = QFrame()
        hdr_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f172a, stop:1 #1e1b4b);
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 12px 18px;
            }
        """)
        hdr_layout = QHBoxLayout(hdr_frame)
        hdr_layout.setContentsMargins(6, 4, 6, 4)
        hdr_layout.setSpacing(14)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(3)
        
        lbl_title_row = QHBoxLayout()
        lbl_title_row.setSpacing(10)
        
        lbl_title = QLabel("🔥 Viral Prompts Library")
        lbl_title.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: 800;")
        lbl_title_row.addWidget(lbl_title)

        # 200+ Viral Prompts Badge
        lbl_badge = QLabel("✨ 200+ Viral Prompts")
        lbl_badge.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c4dff, stop:1 #00e676);
                color: #ffffff;
                font-size: 11px;
                font-weight: 800;
                padding: 3px 10px;
                border-radius: 10px;
            }
        """)
        lbl_title_row.addWidget(lbl_badge)
        lbl_title_row.addStretch()
        title_vbox.addLayout(lbl_title_row)

        lbl_sub = QLabel("Explore production-ready master prompts with direct copy and automation integration.")
        lbl_sub.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_vbox.addWidget(lbl_sub)
        hdr_layout.addLayout(title_vbox, stretch=1)

        # Action Buttons
        self.btn_open_folder = QPushButton("📁 Open Prompts Folder")
        self.btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_folder.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #e2e8f0;
                font-size: 12px;
                font-weight: 600;
                border: 1px solid #475569;
                padding: 7px 14px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #38bdf8;
                color: #38bdf8;
            }
        """)
        self.btn_open_folder.clicked.connect(self._open_folder)
        hdr_layout.addWidget(self.btn_open_folder)

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #e2e8f0;
                font-size: 12px;
                font-weight: 600;
                border: 1px solid #475569;
                padding: 7px 14px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #a855f7;
                color: #c084fc;
            }
        """)
        self.btn_refresh.clicked.connect(self._refresh_library)
        hdr_layout.addWidget(self.btn_refresh)

        main_layout.addWidget(hdr_frame)

        # ── Search & Filter Controls ─────────────────────────────────────────
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(12)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search viral prompts by title, keywords, or content...")
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
            }
        """)
        self.txt_search.textChanged.connect(self._filter_prompts)
        filter_bar.addWidget(self.txt_search, stretch=3)

        self.cmb_category = QComboBox()
        self.cmb_category.setStyleSheet("""
            QComboBox {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12.5px;
                font-weight: 600;
                min-width: 170px;
            }
            QComboBox:hover {
                border-color: #64748b;
            }
            QComboBox QAbstractItemView {
                background-color: #0f172a;
                color: #f8fafc;
                selection-background-color: #2563eb;
                border: 1px solid #334155;
            }
        """)
        self.cmb_category.currentTextChanged.connect(self._filter_prompts)
        filter_bar.addWidget(self.cmb_category, stretch=1)

        self.lbl_count_badge = QLabel("Showing 0 prompts")
        self.lbl_count_badge.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600; padding: 0 6px;")
        filter_bar.addWidget(self.lbl_count_badge)

        main_layout.addLayout(filter_bar)

        # ── Main Split View (List Left, Details Right) ────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #1e293b;
                width: 2px;
            }
        """)

        # Left List Widget
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.setSpacing(6)

        self.prompt_list = QListWidget()
        self.prompt_list.setStyleSheet("""
            QListWidget {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 4px;
            }
            QListWidget::item {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                margin: 3px 2px;
                padding: 10px 12px;
            }
            QListWidget::item:hover {
                background-color: #26334d;
                border-color: #475569;
            }
            QListWidget::item:selected {
                background-color: #1d4ed8;
                border: 1px solid #60a5fa;
                color: #ffffff;
            }
        """)
        self.prompt_list.currentRowChanged.connect(self._on_prompt_selected)
        left_layout.addWidget(self.prompt_list)
        splitter.addWidget(left_container)

        # Right Detail Container
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(6, 0, 0, 0)
        right_layout.setSpacing(10)

        # Detail Header & Action Toolbar
        self.detail_card = QFrame()
        self.detail_card.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 14px 16px;
            }
        """)
        detail_header_layout = QVBoxLayout(self.detail_card)
        detail_header_layout.setSpacing(10)

        top_info_row = QHBoxLayout()
        top_info_row.setSpacing(10)

        self.lbl_detail_title = QLabel("Select a prompt to view details")
        self.lbl_detail_title.setWordWrap(True)
        self.lbl_detail_title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 800;")
        top_info_row.addWidget(self.lbl_detail_title, stretch=1)

        self.lbl_detail_category = QLabel("")
        self.lbl_detail_category.setStyleSheet("""
            background-color: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            font-size: 11px;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 8px;
            border: 1px solid rgba(56, 189, 248, 0.3);
        """)
        top_info_row.addWidget(self.lbl_detail_category)
        detail_header_layout.addLayout(top_info_row)

        # Metadata Row
        meta_row = QHBoxLayout()
        meta_row.setSpacing(14)
        self.lbl_detail_meta = QLabel("")
        self.lbl_detail_meta.setStyleSheet("color: #94a3b8; font-size: 11.5px;")
        meta_row.addWidget(self.lbl_detail_meta)
        meta_row.addStretch()

        # Action Buttons
        self.btn_copy = QPushButton("📋  Copy Prompt")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
                color: #ffffff;
                font-size: 12.5px;
                font-weight: 800;
                padding: 7px 18px;
                border-radius: 8px;
                border: 1px solid #34d399;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #10b981);
            }
        """)
        self.btn_copy.clicked.connect(self._copy_prompt_to_clipboard)
        meta_row.addWidget(self.btn_copy)

        self.btn_add_to_my_prompts = QPushButton("➕  Add to My Prompts")
        self.btn_add_to_my_prompts.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_to_my_prompts.setStyleSheet("""
            QPushButton {
                background-color: rgba(124, 77, 255, 0.2);
                color: #c7d2fe;
                font-size: 12px;
                font-weight: 700;
                padding: 7px 14px;
                border-radius: 8px;
                border: 1px solid #7c4dff;
            }
            QPushButton:hover {
                background-color: #7c4dff;
                color: #ffffff;
            }
        """)
        self.btn_add_to_my_prompts.clicked.connect(self._save_to_user_database)
        meta_row.addWidget(self.btn_add_to_my_prompts)

        self.btn_export_txt = QPushButton("📄  Export TXT")
        self.btn_export_txt.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_txt.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #cbd5e1;
                font-size: 12px;
                font-weight: 600;
                padding: 7px 12px;
                border-radius: 8px;
                border: 1px solid #475569;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #ffffff;
            }
        """)
        self.btn_export_txt.clicked.connect(self._export_txt)
        meta_row.addWidget(self.btn_export_txt)

        detail_header_layout.addLayout(meta_row)
        right_layout.addWidget(self.detail_card)

        # Uncorrupted Prompt Text Editor
        self.txt_content = QTextEdit()
        self.txt_content.setReadOnly(True)
        self.txt_content.setStyleSheet("""
            QTextEdit {
                background-color: #0b0f19;
                color: #f1f5f9;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13.5px;
                line-height: 1.6;
                border: 1.5px solid #334155;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        right_layout.addWidget(self.txt_content, stretch=1)
        splitter.addWidget(right_container)

        splitter.setSizes([340, 660])
        main_layout.addWidget(splitter, stretch=1)

    def _load_prompts_data(self, force_refresh: bool = False):
        """Loads categories and populates the prompt list."""
        all_prompts = viral_prompt_manager.load_all_prompts(force_refresh=force_refresh)
        
        # Populate Category combo
        current_cat = self.cmb_category.currentText() or "All Categories"
        self.cmb_category.blockSignals(True)
        self.cmb_category.clear()
        categories = viral_prompt_manager.get_categories()
        self.cmb_category.addItems(categories)
        if current_cat in categories:
            self.cmb_category.setCurrentText(current_cat)
        self.cmb_category.blockSignals(False)

        self._filter_prompts()

    def _filter_prompts(self):
        """Filters list widget based on search query and category."""
        query = self.txt_search.text()
        category = self.cmb_category.currentText() or "All Categories"

        filtered = viral_prompt_manager.search_prompts(query=query, category=category)
        self.prompt_list.clear()

        for p in filtered:
            item = QListWidgetItem()
            item_text = f"📄  {p['title']}\n    📁 {p['category']} • {p['word_count']} words"
            item.setText(item_text)
            item.setData(Qt.ItemDataRole.UserRole, p)
            self.prompt_list.addItem(item)

        self.lbl_count_badge.setText(f"Showing {len(filtered)} prompts")

        if filtered:
            self.prompt_list.setCurrentRow(0)
        else:
            self._current_selected_prompt = None
            self.lbl_detail_title.setText("No matching prompts found")
            self.lbl_detail_category.setText("")
            self.lbl_detail_meta.setText("Try clearing the search filter or adding new HTML prompt files.")
            self.txt_content.setPlainText("")

    def _on_prompt_selected(self, row: int):
        """Displays details for the selected prompt."""
        item = self.prompt_list.item(row)
        if not item:
            return

        prompt = item.data(Qt.ItemDataRole.UserRole)
        if not prompt:
            return

        self._current_selected_prompt = prompt
        self.lbl_detail_title.setText(prompt["title"])
        self.lbl_detail_category.setText(f"📁 {prompt['category']}")
        self.lbl_detail_meta.setText(f"📊 {prompt['word_count']} words | {prompt['char_count']} characters | 📄 {prompt['filename']}")
        self.txt_content.setPlainText(prompt["content"])

    def _copy_prompt_to_clipboard(self):
        """Copies full prompt text to system clipboard with visual feedback."""
        if not self._current_selected_prompt or not self._current_selected_prompt.get("content"):
            QMessageBox.warning(self, "Copy Prompt", "Please select a prompt first.")
            return

        text = self._current_selected_prompt["content"]
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

        # Visual toast button animation
        orig_style = self.btn_copy.styleSheet()
        self.btn_copy.setText("✓ Copied to Clipboard!")
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background: #059669;
                color: #ffffff;
                font-size: 12.5px;
                font-weight: 800;
                padding: 7px 18px;
                border-radius: 8px;
                border: 2px solid #34d399;
            }
        """)

        QTimer.singleShot(1800, lambda: self._reset_copy_button(orig_style))

    def _reset_copy_button(self, orig_style: str):
        self.btn_copy.setText("📋  Copy Prompt")
        self.btn_copy.setStyleSheet(orig_style)

    def _save_to_user_database(self):
        """Imports viral prompt into user's personal SQLite database."""
        if not self._current_selected_prompt:
            QMessageBox.warning(self, "Add Prompt", "Please select a prompt first.")
            return

        success = viral_prompt_manager.add_to_my_prompts(self._current_selected_prompt)
        if success:
            QMessageBox.information(
                self,
                "Prompt Added",
                f"✅ Successfully added '{self._current_selected_prompt['title']}' to your personal Prompts tab!"
            )
        else:
            QMessageBox.critical(self, "Error", "Failed to save prompt to database.")

    def _export_txt(self):
        """Exports selected prompt to a .txt file."""
        if not self._current_selected_prompt:
            return

        default_name = f"{self._current_selected_prompt['title']}.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Prompt as TXT", default_name, "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self._current_selected_prompt["content"])
                QMessageBox.information(self, "Export Successful", f"Prompt exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Could not export file: {e}")

    def _open_folder(self):
        """Opens viral prompts storage directory in Windows Explorer."""
        viral_prompt_manager.open_folder_in_explorer()

    def _refresh_library(self):
        """Reloads prompts from disk."""
        self._load_prompts_data(force_refresh=True)
