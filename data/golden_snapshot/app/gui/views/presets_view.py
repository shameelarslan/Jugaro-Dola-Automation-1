"""
Presets View displaying default generation templates (TikTok 9:16 10s, Widescreen, Square).
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView
)
from app.managers.preset_manager import PresetManager

class PresetsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        lbl_title = QLabel("GENERATION PRESETS")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #f8fafc;")
        main_layout.addWidget(lbl_title)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Preset Name", "Model", "Aspect Ratio", "Duration", "Description"])
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        presets = PresetManager.get_all_presets()
        table.setRowCount(len(presets))
        for r, p in enumerate(presets):
            table.setItem(r, 0, QTableWidgetItem(p.name))
            table.setItem(r, 1, QTableWidgetItem(p.model))
            table.setItem(r, 2, QTableWidgetItem(p.ratio))
            table.setItem(r, 3, QTableWidgetItem(f"{p.duration}s"))
            table.setItem(r, 4, QTableWidgetItem(p.description))

        main_layout.addWidget(table)
