"""
Modern Commercial SaaS Dark Theme QSS for Waqas's Automation Software (2026 Edition).
Clean, high-contrast, obsidian dark glass, vibrant gradient highlights, and crisp modern typography.
"""

DARK_THEME_QSS = """
QMainWindow, QDialog {
    background-color: #070913;
    color: #f8fafc;
}

QWidget {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    color: #f8fafc;
    font-size: 13px;
}

/* Sidebar Navigation */
QListWidget#sidebar {
    background-color: #0c101d;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
    outline: none;
    font-size: 13px;
    font-weight: 600;
    padding-top: 10px;
}

QListWidget#sidebar::item {
    height: 44px;
    padding-left: 14px;
    color: #94a3b8;
    border-left: 4px solid transparent;
    margin: 3px 8px;
    border-radius: 8px;
}

QListWidget#sidebar::item:hover {
    background-color: rgba(255, 255, 255, 0.06);
    color: #ffffff;
}

QListWidget#sidebar::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8b5cf6, stop:1 #6366f1);
    color: #ffffff;
    border-left: 4px solid #ffffff;
    font-weight: 700;
}

/* Push Buttons */
QPushButton {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid rgba(255, 255, 255, 0.12);
    padding: 8px 18px;
    border-radius: 8px;
    font-weight: 700;
    font-size: 12px;
}

QPushButton:hover {
    background-color: #334155;
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.25);
}

QPushButton:pressed {
    background-color: #0f172a;
}

QPushButton:disabled {
    background-color: #0f172a;
    color: #475569;
    border-color: rgba(255, 255, 255, 0.05);
}

QPushButton#btn_primary, QPushButton#btn_success {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.2);
}

QPushButton#btn_primary:hover, QPushButton#btn_success:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #047857);
}

QPushButton#btn_danger {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f43f5e, stop:1 #e11d48);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.2);
}

QPushButton#btn_danger:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e11d48, stop:1 #be123c);
}

QPushButton#btn_warning {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f59e0b, stop:1 #d97706);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.2);
}

QPushButton#btn_warning:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #d97706, stop:1 #b45309);
}

QPushButton#btn_secondary {
    background-color: rgba(255, 255, 255, 0.06);
    color: #e2e8f0;
    border: 1px solid rgba(255, 255, 255, 0.12);
}

QPushButton#btn_secondary:hover {
    background-color: rgba(255, 255, 255, 0.12);
}

QPushButton#btn_purple {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8b5cf6, stop:1 #6366f1);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.2);
}

QPushButton#btn_purple:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c3aed, stop:1 #4f46e5);
}

/* Cards & Frames */
QFrame#card {
    background-color: rgba(19, 24, 44, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
}

QGroupBox {
    background-color: rgba(19, 24, 44, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    margin-top: 16px;
    font-weight: 700;
    font-size: 13px;
    color: #f8fafc;
    padding-top: 18px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 8px;
    color: #38bdf8;
}

/* Tables */
QTableWidget {
    background-color: #070913;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    gridline-color: rgba(255, 255, 255, 0.05);
    color: #f8fafc;
    selection-background-color: rgba(139, 92, 246, 0.3);
    selection-color: #ffffff;
}

QHeaderView::section {
    background-color: #0c101d;
    color: #94a3b8;
    padding: 10px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

QTableWidget::item {
    padding: 8px;
}

QTableWidget::item:hover {
    background-color: rgba(255, 255, 255, 0.04);
}

/* Inputs & Dropdowns */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
    background-color: #0a0e1a;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 8px 12px;
    color: #f8fafc;
    font-size: 13px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #8b5cf6;
    background-color: #0d1222;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #0c101d;
    color: #f8fafc;
    border: 1px solid rgba(255, 255, 255, 0.12);
    selection-background-color: #8b5cf6;
    selection-color: #ffffff;
}

/* Progress Bar */
QProgressBar {
    background-color: #0c101d;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    font-weight: 700;
    font-size: 11px;
    height: 20px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8b5cf6, stop:1 #38bdf8);
    border-radius: 5px;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: #070913;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: rgba(255, 255, 255, 0.15);
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: rgba(139, 92, 246, 0.6);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""
