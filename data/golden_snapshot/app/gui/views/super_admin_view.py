"""
Super Admin Cloud Dashboard View - Clean, High-Contrast Executive SaaS Control Center.
Features sleek KPI cards, a segmented tab switcher between Creator Directory and Live Activity,
and zero visual clutter (no awkward white boxes or cramped stacked tables).
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QMessageBox, QLineEdit, QStackedWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from app.core.cloud_manager import cloud_manager

class SuperAdminStatsWorker(QThread):
    stats_loaded = pyqtSignal(dict)

    def run(self):
        data = cloud_manager.fetch_super_dashboard_stats()
        self.stats_loaded.emit(data)

class SuperAdminView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker_thread = None
        self._raw_users_data = []
        self._raw_activities_data = []
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 18)
        main_layout.setSpacing(14)

        # ── 1. Top Control Bar ───────────────────────────────────────────────
        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        header_card.setStyleSheet("""
            QFrame#HeaderCard {
                background-color: #111424;
                border: 1px solid rgba(124, 77, 255, 0.35);
                border-radius: 12px;
                padding: 10px 16px;
            }
        """)
        
        hdr_layout = QHBoxLayout(header_card)
        hdr_layout.setContentsMargins(4, 2, 4, 2)
        hdr_layout.setSpacing(14)

        crown_lbl = QLabel("👑")
        crown_lbl.setFixedSize(40, 40)
        crown_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        crown_lbl.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7c4dff, stop:1 #4f46e5);
            font-size: 20px;
            border-radius: 20px;
            border: 2px solid rgba(255, 255, 255, 0.2);
        """)
        hdr_layout.addWidget(crown_lbl)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        
        lbl_title = QLabel("Super Admin Control Center")
        lbl_title.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: 900;")
        
        lbl_sub = QLabel("Multi-user creator approvals, license control & real-time cloud activity")
        lbl_sub.setStyleSheet("color: #8f9bb3; font-size: 12px;")
        
        title_vbox.addWidget(lbl_title)
        title_vbox.addWidget(lbl_sub)
        hdr_layout.addLayout(title_vbox)

        hdr_layout.addStretch()

        self.btn_refresh = QPushButton("🔄  Sync Live Cloud Data")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #7c3aed);
                color: #ffffff;
                font-weight: 800;
                font-size: 12px;
                border: none;
                border-radius: 8px;
                padding: 9px 18px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #6d28d9);
            }
        """)
        self.btn_refresh.clicked.connect(self.refresh_stats)
        hdr_layout.addWidget(self.btn_refresh)

        main_layout.addWidget(header_card)

        # ── 2. Four Executive Cyber KPI Metric Cards ─────────────────────────
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.card_users, self.val_users, self.pill_users = self._create_kpi_card(
            title="TOTAL CREATORS",
            icon="👥",
            init_val="0",
            pill_text="Registered Users",
            pill_color="#c084fc",
            border_accent="#8b5cf6",
            bg_color="#121528"
        )
        
        self.card_pending, self.val_pending, self.pill_pending = self._create_kpi_card(
            title="PENDING APPROVALS",
            icon="⏳",
            init_val="0",
            pill_text="All Accounts Approved",
            pill_color="#34d399",
            border_accent="#f59e0b",
            bg_color="#161520"
        )

        self.card_total_vids, self.val_total_vids, self.pill_total_vids = self._create_kpi_card(
            title="ALL-TIME VIDEOS",
            icon="🎬",
            init_val="0",
            pill_text="Clean Watermark-Free MP4s",
            pill_color="#34d399",
            border_accent="#10b981",
            bg_color="#101820"
        )

        self.card_today_vids, self.val_today_vids, self.pill_today_vids = self._create_kpi_card(
            title="TODAY'S VIDEOS",
            icon="🔥",
            init_val="0",
            pill_text="Generated Last 24 Hours",
            pill_color="#38bdf8",
            border_accent="#06b6d4",
            bg_color="#101624"
        )

        cards_layout.addWidget(self.card_users)
        cards_layout.addWidget(self.card_pending)
        cards_layout.addWidget(self.card_total_vids)
        cards_layout.addWidget(self.card_today_vids)

        main_layout.addLayout(cards_layout)

        # ── 3. Segmented Navigation Bar (Switch Between Users & Live Feed) ───
        nav_bar = QHBoxLayout()
        nav_bar.setSpacing(10)

        # Segmented Button 1: Creator Directory
        self.btn_tab_users = QPushButton("👥   Creator Directory & Approvals (0)")
        self.btn_tab_users.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_users.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                font-size: 13px;
                font-weight: 800;
                border: 1px solid #3b82f6;
                border-radius: 8px;
                padding: 8px 18px;
            }
        """)
        self.btn_tab_users.clicked.connect(lambda: self._switch_content_tab(0))
        nav_bar.addWidget(self.btn_tab_users)

        # Segmented Button 2: Live Activity Feed
        self.btn_tab_feed = QPushButton("⚡   Live Video Activity Stream (0)")
        self.btn_tab_feed.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_feed.setStyleSheet("""
            QPushButton {
                background-color: #121526;
                color: #94a3b8;
                font-size: 13px;
                font-weight: 700;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 8px 18px;
            }
            QPushButton:hover {
                background-color: #1e2438;
                color: #ffffff;
            }
        """)
        self.btn_tab_feed.clicked.connect(lambda: self._switch_content_tab(1))
        nav_bar.addWidget(self.btn_tab_feed)

        nav_bar.addStretch()

        # Search box (Visible on Users Tab)
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search creators by name or email...")
        self.txt_search.setFixedWidth(300)
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background-color: #121526;
                color: #ffffff;
                border: 1px solid rgba(124, 77, 255, 0.35);
                border-radius: 8px;
                padding: 7px 12px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #7c4dff;
                background-color: #171d33;
            }
        """)
        self.txt_search.textChanged.connect(self._filter_users_table)
        nav_bar.addWidget(self.txt_search)

        main_layout.addLayout(nav_bar)

        # ── 4. Stacked Content Area (Clean, Full-Height Tables) ───────────────
        self.content_stack = QStackedWidget()

        # ── TAB 0: Creator Directory Table ──
        self.table_users = QTableWidget()
        self.table_users.setColumnCount(8)
        self.table_users.setHorizontalHeaderLabels([
            "Status", "Creator Name", "Email Address", "WhatsApp", "Total Videos", "Today's Videos", "Registered Date", "License Action"
        ])
        self._format_clean_table(self.table_users)
        self.table_users.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_users.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_users.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_users.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table_users.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table_users.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table_users.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.content_stack.addWidget(self.table_users)

        # ── TAB 1: Live Activity Feed Table ──
        self.table_feed = QTableWidget()
        self.table_feed.setColumnCount(5)
        self.table_feed.setHorizontalHeaderLabels([
            "Time (UTC)", "Creator Email", "Generated Video File", "File Size", "Cloud Status"
        ])
        self._format_clean_table(self.table_feed)
        self.table_feed.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_feed.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_feed.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_feed.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.content_stack.addWidget(self.table_feed)

        main_layout.addWidget(self.content_stack, stretch=1)

    def _format_clean_table(self, table: QTableWidget):
        """Applies unified, ultra-clean dark SaaS table styling with NO white boxes."""
        table.verticalHeader().setVisible(False)  # Permanently hides row numbers & removes white box!
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setStyleSheet("""
            QTableWidget {
                background-color: #0e1220;
                border: 1px solid rgba(124, 77, 255, 0.25);
                border-radius: 10px;
                color: #ffffff;
                font-size: 13px;
                gridline-color: rgba(255, 255, 255, 0.05);
            }
            QHeaderView::section {
                background-color: #151930;
                color: #94a3b8;
                font-weight: 800;
                font-size: 12px;
                padding: 11px 12px;
                border: none;
                border-bottom: 1px solid rgba(124, 77, 255, 0.35);
            }
            QTableCornerButton::section {
                background-color: #151930;
                border: none;
            }
            QTableWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            }
            QTableWidget::item:selected {
                background-color: #1e293b;
                color: #ffffff;
            }
        """)

    def _create_kpi_card(self, title: str, icon: str, init_val: str, pill_text: str, pill_color: str, border_accent: str, bg_color: str):
        card = QFrame()
        card.setObjectName("KpiCard")
        card.setStyleSheet(f"""
            QFrame#KpiCard {{
                background-color: {bg_color};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-top: 3px solid {border_accent};
                border-radius: 12px;
                padding: 12px 14px;
            }}
        """)
        
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(8, 6, 8, 6)
        vbox.setSpacing(4)

        # Top Row
        top_row = QHBoxLayout()
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 800; letter-spacing: 0.5px;")
        
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet("font-size: 14px;")
        
        top_row.addWidget(lbl_t)
        top_row.addStretch()
        top_row.addWidget(lbl_icon)
        vbox.addLayout(top_row)

        # Value Number (Big 34px Bold)
        lbl_v = QLabel(init_val)
        lbl_v.setStyleSheet(f"""
            color: #ffffff;
            font-size: 34px;
            font-weight: 900;
            font-family: 'Segoe UI', Inter, sans-serif;
        """)
        vbox.addWidget(lbl_v)

        # Subtext Pill
        lbl_pill = QLabel(pill_text)
        lbl_pill.setStyleSheet(f"""
            color: {pill_color};
            font-size: 11px;
            font-weight: 700;
        """)
        vbox.addWidget(lbl_pill)

        return card, lbl_v, lbl_pill

    def _switch_content_tab(self, tab_index: int):
        self.content_stack.setCurrentIndex(tab_index)
        
        if tab_index == 0:
            self.btn_tab_users.setStyleSheet("""
                QPushButton {
                    background-color: #2563eb;
                    color: #ffffff;
                    font-size: 13px;
                    font-weight: 800;
                    border: 1px solid #3b82f6;
                    border-radius: 8px;
                    padding: 8px 18px;
                }
            """)
            self.btn_tab_feed.setStyleSheet("""
                QPushButton {
                    background-color: #121526;
                    color: #94a3b8;
                    font-size: 13px;
                    font-weight: 700;
                    border: 1px solid #1e293b;
                    border-radius: 8px;
                    padding: 8px 18px;
                }
                QPushButton:hover {
                    background-color: #1e2438;
                    color: #ffffff;
                }
            """)
            self.txt_search.setVisible(True)
        else:
            self.btn_tab_users.setStyleSheet("""
                QPushButton {
                    background-color: #121526;
                    color: #94a3b8;
                    font-size: 13px;
                    font-weight: 700;
                    border: 1px solid #1e293b;
                    border-radius: 8px;
                    padding: 8px 18px;
                }
                QPushButton:hover {
                    background-color: #1e2438;
                    color: #ffffff;
                }
            """)
            self.btn_tab_feed.setStyleSheet("""
                QPushButton {
                    background-color: #2563eb;
                    color: #ffffff;
                    font-size: 13px;
                    font-weight: 800;
                    border: 1px solid #3b82f6;
                    border-radius: 8px;
                    padding: 8px 18px;
                }
            """)
            self.txt_search.setVisible(False)

    def refresh_stats(self):
        """Fetches latest cloud statistics in a background thread."""
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText("🔄  Syncing Cloud...")

        self.worker_thread = SuperAdminStatsWorker()
        self.worker_thread.stats_loaded.connect(self._on_stats_loaded)
        self.worker_thread.start()

    def _on_stats_loaded(self, data: dict):
        self.btn_refresh.setEnabled(True)
        self.btn_refresh.setText("🔄  Sync Live Cloud Data")

        # 1. Update KPI Numbers
        total_u = data.get("total_users", 0)
        self.val_users.setText(str(total_u))
        
        pending_cnt = data.get("pending_users", 0)
        self.val_pending.setText(str(pending_cnt))
        if pending_cnt > 0:
            self.val_pending.setStyleSheet("color: #fbbf24; font-size: 34px; font-weight: 900;")
            self.pill_pending.setText(f"⚠️ {pending_cnt} Account(s) Waiting Approval")
            self.pill_pending.setStyleSheet("color: #fbbf24; font-size: 11px; font-weight: 800;")
        else:
            self.val_pending.setStyleSheet("color: #34d399; font-size: 34px; font-weight: 900;")
            self.pill_pending.setText("✓ All Accounts Approved & Active")
            self.pill_pending.setStyleSheet("color: #34d399; font-size: 11px; font-weight: 700;")

        self.val_total_vids.setText(str(data.get("total_videos_all_time", 0)))
        self.val_today_vids.setText(str(data.get("today_videos", 0)))

        # Update Tab counts
        users = data.get("all_users", [])
        activities = data.get("recent_activity", [])
        self._raw_users_data = users
        self._raw_activities_data = activities

        self.btn_tab_users.setText(f"👥   Creator Directory & Approvals ({len(users)})")
        self.btn_tab_feed.setText(f"⚡   Live Video Activity Stream ({len(activities)})")

        self._render_users_table(self._raw_users_data)
        self._render_activity_feed(self._raw_activities_data)

    def _filter_users_table(self, query: str):
        query = (query or "").strip().lower()
        if not query:
            self._render_users_table(self._raw_users_data)
            return

        filtered = [
            u for u in self._raw_users_data
            if query in u.get("name", "").lower() or query in u.get("email", "").lower()
        ]
        self._render_users_table(filtered)

    def _render_users_table(self, users: list):
        self.table_users.setRowCount(len(users))

        for row, u in enumerate(users):
            status = u.get("status", "Pending")
            user_id = u.get("user_id")

            # 1. Status Column
            if status == "Active":
                status_text = "🟢 Active"
                status_color = "#10b981"
            elif status == "Pending":
                status_text = "🟡 Pending Approval"
                status_color = "#fbbf24"
            else:
                status_text = "🔴 Blocked"
                status_color = "#ef4444"

            item_status = QTableWidgetItem(status_text)
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_status.setForeground(QColor(status_color))
            font_s = item_status.font()
            font_s.setBold(True)
            item_status.setFont(font_s)
            self.table_users.setItem(row, 0, item_status)

            # 2. Creator Name
            item_name = QTableWidgetItem(u.get("name", "User"))
            item_name.setForeground(QColor("#ffffff"))
            font_n = item_name.font()
            font_n.setBold(True)
            item_name.setFont(font_n)
            self.table_users.setItem(row, 1, item_name)

            # 3. Email Address
            item_email = QTableWidgetItem(u.get("email", ""))
            item_email.setForeground(QColor("#cbd5e1"))
            self.table_users.setItem(row, 2, item_email)

            # 4. WhatsApp Number
            whatsapp = u.get("whatsapp_number", "") or "—"
            item_whatsapp = QTableWidgetItem(f"📱 {whatsapp}" if whatsapp != "—" else "—")
            item_whatsapp.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_whatsapp.setForeground(QColor("#25D366"))
            font_wa = item_whatsapp.font()
            font_wa.setBold(True)
            item_whatsapp.setFont(font_wa)
            self.table_users.setItem(row, 3, item_whatsapp)

            # 5. Total Videos
            item_tot = QTableWidgetItem(f"🎬 {u.get('total_videos', 0)}")
            item_tot.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_tot.setForeground(QColor("#34d399"))
            font_tot = item_tot.font()
            font_tot.setBold(True)
            item_tot.setFont(font_tot)
            self.table_users.setItem(row, 4, item_tot)

            # 6. Today's Videos
            item_tdy = QTableWidgetItem(f"🔥 {u.get('today_videos', 0)}")
            item_tdy.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_tdy.setForeground(QColor("#38bdf8"))
            font_tdy = item_tdy.font()
            font_tdy.setBold(True)
            item_tdy.setFont(font_tdy)
            self.table_users.setItem(row, 5, item_tdy)

            # 7. Registered Date
            created_str = u.get("created_at", "")[:10]
            item_date = QTableWidgetItem(created_str)
            item_date.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_date.setForeground(QColor("#94a3b8"))
            self.table_users.setItem(row, 6, item_date)

            # 7. Action Button Widget
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(6, 2, 6, 2)
            btn_layout.setSpacing(8)

            if status == "Pending":
                btn_approve = QPushButton("✅ Approve")
                btn_approve.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_approve.setStyleSheet("""
                    QPushButton {
                        background-color: #123320;
                        color: #10b981;
                        border: 1px solid #10b981;
                        border-radius: 6px;
                        font-weight: 800;
                        font-size: 11px;
                        padding: 5px 12px;
                    }
                    QPushButton:hover {
                        background-color: #10b981;
                        color: #000000;
                    }
                """)
                btn_approve.clicked.connect(lambda checked, uid=user_id: self._handle_set_status(uid, "Active"))
                btn_layout.addWidget(btn_approve)

                btn_reject = QPushButton("🚫 Reject")
                btn_reject.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_reject.setStyleSheet("""
                    QPushButton {
                        background-color: #3b1820;
                        color: #ef4444;
                        border: 1px solid #ef4444;
                        border-radius: 6px;
                        font-weight: 800;
                        font-size: 11px;
                        padding: 5px 12px;
                    }
                    QPushButton:hover {
                        background-color: #ef4444;
                        color: #ffffff;
                    }
                """)
                btn_reject.clicked.connect(lambda checked, uid=user_id: self._handle_set_status(uid, "Blocked"))
                btn_layout.addWidget(btn_reject)

            elif status == "Active":
                btn_block = QPushButton("🔒 Block Access")
                btn_block.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_block.setStyleSheet("""
                    QPushButton {
                        background-color: #2a151d;
                        color: #f87171;
                        border: 1px solid rgba(239, 68, 68, 0.4);
                        border-radius: 6px;
                        font-weight: 700;
                        font-size: 11px;
                        padding: 5px 12px;
                    }
                    QPushButton:hover {
                        background-color: #ef4444;
                        color: #ffffff;
                    }
                """)
                btn_block.clicked.connect(lambda checked, uid=user_id: self._handle_set_status(uid, "Blocked"))
                btn_layout.addWidget(btn_block)

            else:  # Blocked
                btn_unblock = QPushButton("🔓 Unblock Access")
                btn_unblock.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_unblock.setStyleSheet("""
                    QPushButton {
                        background-color: #123320;
                        color: #34d399;
                        border: 1px solid rgba(16, 185, 129, 0.4);
                        border-radius: 6px;
                        font-weight: 700;
                        font-size: 11px;
                        padding: 5px 12px;
                    }
                    QPushButton:hover {
                        background-color: #10b981;
                        color: #000000;
                    }
                """)
                btn_unblock.clicked.connect(lambda checked, uid=user_id: self._handle_set_status(uid, "Active"))
                btn_layout.addWidget(btn_unblock)

            self.table_users.setCellWidget(row, 7, btn_container)

    def _render_activity_feed(self, activities: list):
        self.table_feed.setRowCount(len(activities))

        for row, act in enumerate(activities):
            created_str = act.get("created_at", "")[:19].replace("T", " ")
            item_time = QTableWidgetItem(created_str)
            item_time.setForeground(QColor("#94a3b8"))

            item_email = QTableWidgetItem(act.get("user_email", ""))
            item_email.setForeground(QColor("#c7d2fe"))

            item_vname = QTableWidgetItem(f"🎬 {act.get('video_name', '')}")
            item_vname.setForeground(QColor("#ffffff"))
            
            sz = act.get("file_size_mb", 0)
            item_sz = QTableWidgetItem(f"💾 {sz} MB" if sz else "—")
            item_sz.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_sz.setForeground(QColor("#38bdf8"))

            item_st = QTableWidgetItem("✅ Completed")
            item_st.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_st.setForeground(QColor("#10b981"))
            font_st = item_st.font()
            font_st.setBold(True)
            item_st.setFont(font_st)

            self.table_feed.setItem(row, 0, item_time)
            self.table_feed.setItem(row, 1, item_email)
            self.table_feed.setItem(row, 2, item_vname)
            self.table_feed.setItem(row, 3, item_sz)
            self.table_feed.setItem(row, 4, item_st)

    def _handle_set_status(self, user_id: str, new_status: str):
        if not user_id:
            return
        ok = cloud_manager.toggle_user_status(user_id, new_status)
        if ok:
            self.refresh_stats()
        else:
            QMessageBox.warning(self, "Error", f"Failed to update user to {new_status}.")
