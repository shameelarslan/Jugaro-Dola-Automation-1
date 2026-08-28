"""
Summary Stat Metric Card Widget for PyQt6 Dashboard.
Compact height design to fit screen without scrolling.
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

class StatCard(QFrame):
    def __init__(self, title: str, initial_value: str = "0", accent_color: str = "#2563eb", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedHeight(68)
        self.setStyleSheet("""
            QFrame {
                background-color: #27272a;
                border: 1px solid #3f3f46;
                border-radius: 6px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setStyleSheet("color: #a1a1aa; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;")
        
        self.lbl_value = QLabel(initial_value)
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_value.setStyleSheet(f"color: {accent_color}; font-size: 22px; font-weight: bold;")
        
        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_value)

    def set_value(self, value: str):
        self.lbl_value.setText(str(value))
