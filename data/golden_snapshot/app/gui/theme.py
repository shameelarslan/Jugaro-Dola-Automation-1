"""
Modern Commercial SaaS Dark Theme QSS for Waqas's Automation Software.
Clean, professional, high-contrast, crystal-clear typography and polished controls.
"""

DARK_THEME_QSS = """
QMainWindow, QDialog {
    background-color: #0f172a;
    color: #f8fafc;
}

QWidget {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    color: #f8fafc;
    font-size: 13px;
}

/* Sidebar Navigation */
QListWidget#sidebar {
    background-color: #1e293b;
    border-right: 1px solid #334155;
    outline: none;
    font-size: 13px;
    font-weight: 500;
    padding-top: 8px;
}

QListWidget#sidebar::item {
    height: 42px;
    padding-left: 14px;
    color: #94a3b8;
    border-left: 4px solid transparent;
    margin: 2px 6px;
    border-radius: 6px;
}

QListWidget#sidebar::item:hover {
    background-color: #334155;
    color: #ffffff;
}

QListWidget#sidebar::item:selected {
    background-color: #2563eb;
    color: #ffffff;
    border-left: 4px solid #60a5fa;
    font-weight: 600;
}

/* Push Buttons */
QPushButton {
    background-color: #334155;
    color: #f8fafc;
    border: 1px solid #475569;
    padding: 7px 16px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton:hover {
    background-color: #475569;
    color: #ffffff;
    border-color: #64748b;
}

QPushButton:pressed {
    background-color: #1e293b;
}

QPushButton:disabled {
    background-color: #1e293b;
    color: #64748b;
    border-color: #334155;
}

QPushButton#btn_primary, QPushButton#btn_success {
    background-color: #16a34a;
    color: #ffffff;
    border: 1px solid #22c55e;
}

QPushButton#btn_primary:hover, QPushButton#btn_success:hover {
    background-color: #15803d;
}

QPushButton#btn_danger {
    background-color: #dc2626;
    color: #ffffff;
    border: 1px solid #ef4444;
}

QPushButton#btn_danger:hover {
    background-color: #b91c1c;
}

QPushButton#btn_warning {
    background-color: #d97706;
    color: #ffffff;
    border: 1px solid #f59e0b;
}

QPushButton#btn_warning:hover {
    background-color: #b45309;
}

QPushButton#btn_secondary {
    background-color: #1e293b;
    color: #e2e8f0;
    border: 1px solid #334155;
}

QPushButton#btn_secondary:hover {
    background-color: #334155;
}

QPushButton#btn_purple {
    background-color: #7c3aed;
    color: #ffffff;
    border: 1px solid #8b5cf6;
}

QPushButton#btn_purple:hover {
    background-color: #6d28d9;
}

/* Cards & Frames */
QFrame#card {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
}

QGroupBox {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 14px;
    font-weight: 600;
    font-size: 13px;
    color: #f8fafc;
    padding-top: 16px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: #93c5fd;
}

/* Tables */
QTableWidget {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    gridline-color: #1e293b;
    color: #f8fafc;
    selection-background-color: #1e3a8a;
    selection-color: #ffffff;
}

QHeaderView::section {
    background-color: #1e293b;
    color: #94a3b8;
    padding: 8px;
    font-size: 12px;
    font-weight: 600;
    border: none;
    border-bottom: 1px solid #334155;
}

QTableWidget::item {
    padding: 6px;
}

QTableWidget::item:hover {
    background-color: #1e293b;
}

/* Inputs & Dropdowns */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f8fafc;
    font-size: 13px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #3b82f6;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

/* Progress Bar */
QProgressBar {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    font-weight: 600;
    font-size: 11px;
    height: 18px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #3b82f6);
    border-radius: 5px;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: #0f172a;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #334155;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""
