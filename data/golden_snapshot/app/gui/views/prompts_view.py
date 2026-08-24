"""
Professional Prompt Management View for Waqas's Automation Software.
Supports bulk prompt paste, TXT/CSV file importing, prompt editing,
exporting, status badges (PENDING, RUNNING, COMPLETED, FAILED, RETRYING),
and quick queue action buttons (Reset Failed, Clear Completed).
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox,
    QGroupBox, QLineEdit, QDialog, QFormLayout, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from app.core.database import db

class EditPromptDialog(QDialog):
    def __init__(self, prompt_id: int, current_text: str, parent=None):
        super().__init__(parent)
        self.prompt_id = prompt_id
        self.setWindowTitle(f"Edit Prompt #{prompt_id}")
        self.setMinimumSize(500, 260)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_prompt = QTextEdit()
        self.txt_prompt.setPlainText(current_text)
        form.addRow("Prompt Text:", self.txt_prompt)
        layout.addLayout(form)

        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

    def get_text(self) -> str:
        return self.txt_prompt.toPlainText().strip()

class PromptsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.load_prompts(force=True)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_prompts)
        self.timer.start(4000)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_prompts(force=True)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # ── 1. Top Header Bar ────────────────────────────────────────────────
        hdr_layout = QHBoxLayout()
        lbl_title = QLabel("Prompt Library")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #f8fafc;")

        self.lbl_count = QLabel("0 Prompts in Queue")
        self.lbl_count.setStyleSheet("color: #94a3b8; font-size: 13px;")

        hdr_layout.addWidget(lbl_title)
        hdr_layout.addSpacing(16)
        hdr_layout.addWidget(self.lbl_count)
        hdr_layout.addStretch()

        btn_import = QPushButton("📥 Import TXT / CSV")
        btn_import.setObjectName("btn_secondary")
        btn_import.clicked.connect(self._on_import_file)

        btn_export = QPushButton("📤 Export Prompts")
        btn_export.setObjectName("btn_secondary")
        btn_export.clicked.connect(self._on_export_file)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self.load_prompts)

        hdr_layout.addWidget(btn_import)
        hdr_layout.addWidget(btn_export)
        hdr_layout.addWidget(btn_refresh)
        main_layout.addLayout(hdr_layout)

        # ── 2. Bulk Prompt Paste Box ─────────────────────────────────────────
        grp_paste = QGroupBox("Quick Paste Prompts (One per line)")
        paste_layout = QVBoxLayout(grp_paste)
        paste_layout.setContentsMargins(12, 16, 12, 12)
        paste_layout.setSpacing(8)

        self.txt_bulk = QTextEdit()
        self.txt_bulk.setPlaceholderText("Paste prompt text here (supports multi-line prompt lists)...")
        self.txt_bulk.setMaximumHeight(85)
        paste_layout.addWidget(self.txt_bulk)

        paste_btn_bar = QHBoxLayout()
        btn_add_pasted = QPushButton("+ Add Prompts to Library")
        btn_add_pasted.setObjectName("btn_success")
        btn_add_pasted.clicked.connect(self._on_add_pasted)

        btn_reset_failed = QPushButton("🔄 Reset Failed")
        btn_reset_failed.setObjectName("btn_secondary")
        btn_reset_failed.clicked.connect(self._on_reset_failed)

        btn_clear_completed = QPushButton("🧹 Clear Completed")
        btn_clear_completed.setObjectName("btn_secondary")
        btn_clear_completed.clicked.connect(self._on_clear_completed)

        btn_delete_selected = QPushButton("🗑 Delete Selected")
        btn_delete_selected.setObjectName("btn_danger")
        btn_delete_selected.clicked.connect(self._on_delete_selected)

        paste_btn_bar.addWidget(btn_add_pasted)
        paste_btn_bar.addSpacing(16)
        paste_btn_bar.addWidget(btn_reset_failed)
        paste_btn_bar.addWidget(btn_clear_completed)
        paste_btn_bar.addWidget(btn_delete_selected)
        paste_btn_bar.addStretch()

        paste_layout.addLayout(paste_btn_bar)
        main_layout.addWidget(grp_paste)

        # ── 3. Search & Filter Bar ───────────────────────────────────────────
        search_bar = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Filter prompts by text or status...")
        self.txt_search.textChanged.connect(self.load_prompts)
        search_bar.addWidget(self.txt_search)
        main_layout.addLayout(search_bar)

        # ── 4. Prompts Management Table ──────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Prompt #", "Prompt Preview", "Status", "Assigned Session", "Attempt", "Created", "Result / MP4"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.doubleClicked.connect(self._on_table_double_clicked)

        main_layout.addWidget(self.table, stretch=1)

    def load_prompts(self, force: bool = False):
        """Fetches prompts and jobs to display up-to-date status table."""
        if not force and not self.isVisible():
            return
        filter_text = self.txt_search.text().strip().lower()

        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT p.id, p.prompt_text, p.status as p_status, p.created_at,
                       j.id as job_id, j.status as j_status, j.retry_count,
                       j.downloaded_filename, s.name as session_name
                FROM prompts p
                LEFT JOIN (
                    SELECT * FROM jobs
                    WHERE rowid IN (
                        SELECT MAX(rowid) FROM jobs GROUP BY prompt_id
                    )
                ) j ON p.id = j.prompt_id
                LEFT JOIN sessions s ON j.session_id = s.id
                ORDER BY p.id DESC
            """)
            rows = cur.fetchall()

        filtered_rows = []
        for r in rows:
            p_text = (r["prompt_text"] or "").lower()
            j_stat = (r["j_status"] or "").lower()
            p_stat = (r["p_status"] or "pending").lower()
            st = j_stat or p_stat
            if not filter_text or filter_text in p_text or filter_text in st:
                filtered_rows.append(r)

        self.lbl_count.setText(f"{len(rows)} Total Prompts in Database")
        self.table.setRowCount(len(filtered_rows))

        for row, r in enumerate(filtered_rows):
            pid = r["id"]
            self.table.setItem(row, 0, QTableWidgetItem(f"#{pid}"))

            # Prompt preview
            preview = (r["prompt_text"] or "").replace("\n", " ")
            if len(preview) > 120:
                preview = preview[:117] + "..."
            self.table.setItem(row, 1, QTableWidgetItem(preview))

            # Status Badge (PENDING, RUNNING, COMPLETED, FAILED, STOPPED, RETRYING)
            j_stat = (r["j_status"] or "").upper()
            p_stat = (r["p_status"] or "PENDING").upper()

            if j_stat == "COMPLETED":
                raw_status = "COMPLETED"
            elif j_stat in ("STARTING", "RUNNING", "GENERATING", "DOWNLOADING"):
                raw_status = "RUNNING"
            elif j_stat in ("FAILED", "ERROR"):
                raw_status = "FAILED"
            elif j_stat == "STOPPED":
                raw_status = "STOPPED"
            elif j_stat == "RETRYING":
                raw_status = "RETRYING"
            else:
                raw_status = p_stat

            item_status = QTableWidgetItem(raw_status)
            if raw_status == "COMPLETED":
                item_status.setForeground(QColor("#10b981"))
            elif raw_status == "RUNNING":
                item_status.setForeground(QColor("#3b82f6"))
            elif raw_status in ("FAILED", "ERROR"):
                item_status.setForeground(QColor("#ef4444"))
            elif raw_status in ("STOPPED", "RETRYING"):
                item_status.setForeground(QColor("#f59e0b"))
            else:
                item_status.setForeground(QColor("#94a3b8"))
            self.table.setItem(row, 2, item_status)

            # Assigned Session: Only display session if actively running or completed; otherwise show Unassigned
            if raw_status in ("RUNNING", "COMPLETED") and r["session_name"]:
                sess_str = r["session_name"]
            else:
                sess_str = "Unassigned"
            self.table.setItem(row, 3, QTableWidgetItem(sess_str))

            # Attempt / Retries
            retries = r["retry_count"] if r["retry_count"] is not None else 0
            self.table.setItem(row, 4, QTableWidgetItem(f"Attempt {retries + 1}"))

            # Created
            c_str = str(r["created_at"] or "")[:19]
            self.table.setItem(row, 5, QTableWidgetItem(c_str))

            # Result / MP4
            dl_file = r["downloaded_filename"] or "-"
            item_dl = QTableWidgetItem(dl_file)
            if dl_file != "-":
                item_dl.setForeground(QColor("#10b981"))
            self.table.setItem(row, 6, item_dl)

    def _on_add_pasted(self):
        text = self.txt_bulk.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Input Empty", "Please paste at least one prompt.")
            return

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines:
            db.add_prompt(line)

        self.txt_bulk.clear()
        self.load_prompts()
        QMessageBox.information(self, "Prompts Added", f"Added {len(lines)} prompt(s) successfully!")

    def _on_import_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Prompts File", "", "Text & CSV Files (*.txt *.csv);;All Files (*.*)")
        if not file_path:
            return

        try:
            added = 0
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    clean = line.strip()
                    if clean:
                        db.add_prompt(clean)
                        added += 1
            self.load_prompts()
            QMessageBox.information(self, "Import Complete", f"Successfully imported {added} prompt(s) from {Path(file_path).name}!")
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import file: {e}")

    def _on_export_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Prompts File", "prompts_export.txt", "Text Files (*.txt);;CSV Files (*.csv)")
        if not file_path:
            return

        try:
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT prompt_text FROM prompts ORDER BY id ASC")
                prompts = [r[0] for r in cur.fetchall()]

            with open(file_path, "w", encoding="utf-8") as f:
                for p in prompts:
                    f.write(p.replace("\n", " ") + "\n")

            QMessageBox.information(self, "Export Complete", f"Exported {len(prompts)} prompts to {Path(file_path).name}!")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export prompts: {e}")

    def _on_table_double_clicked(self, index):
        row = index.row()
        pid_item = self.table.item(row, 0)
        if not pid_item:
            return

        pid = int(pid_item.text().replace("#", ""))
        prompt_record = db.get_prompt(pid)
        if not prompt_record:
            return

        dlg = EditPromptDialog(pid, prompt_record["prompt_text"], self)
        if dlg.exec():
            new_text = dlg.get_text()
            if new_text:
                with db.get_connection() as conn:
                    conn.cursor().execute("UPDATE prompts SET prompt_text = ? WHERE id = ?", (new_text, pid))
                    conn.commit()
                self.load_prompts()

    def _on_delete_selected(self):
        selection = self.table.selectionModel().selectedRows()
        if selection:
            rows = [idx.row() for idx in selection]
        else:
            rows = list(set(item.row() for item in self.table.selectedItems()))

        if not rows:
            QMessageBox.information(self, "Notice", "Please select at least one prompt row to delete.")
            return

        pids = []
        for r in rows:
            item = self.table.item(r, 0)
            if item and item.text().startswith("#"):
                try:
                    pids.append(int(item.text().replace("#", "")))
                except ValueError:
                    pass

        if not pids:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete {len(pids)} selected prompt(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            for pid in pids:
                db.delete_prompt(pid)
            self.table.clearSelection()
            self.load_prompts()

    def _on_reset_failed(self):
        db.retry_failed_jobs()
        self.load_prompts()
        QMessageBox.information(self, "Reset Complete", "Failed jobs reset to Pending.")

    def _on_clear_completed(self):
        with db.get_connection() as conn:
            conn.cursor().execute("DELETE FROM jobs WHERE status = 'Completed'")
            conn.commit()
        self.load_prompts()
        QMessageBox.information(self, "Cleaned", "Completed jobs cleared from history.")
