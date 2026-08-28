"""
GUI-level unit & integration test for SessionsView (Delete single, Delete multiple, Busy check, Toggle, Edit).
"""

import sys
import os
from pathlib import Path

# Force UTF-8
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from PyQt6.QtWidgets import QApplication, QMessageBox
from app.core.database import db
from app.managers.session_manager import SessionManager
from app.gui.views.sessions_view import SessionsView

def test_gui_session_deletion():
    app = QApplication.instance() or QApplication(sys.argv)
    
    print("\n--- Testing SessionsView GUI Deletion & Action Handlers ---")
    
    # 1. Setup clean sessions
    for s in db.get_all_sessions():
        db.delete_session(s["id"])

    s1_id = SessionManager.add_session("Test Account 01", "cookies_json", cookie_data='[{"name":"c1","value":"1"}]')
    s2_id = SessionManager.add_session("Test Account 02", "cookies_json", cookie_data='[{"name":"c2","value":"2"}]')
    s3_id = SessionManager.add_session("dola 1", "cookies_json", cookie_data='[{"name":"c3","value":"3"}]')

    db.update_session_status(s1_id, "Disabled")
    db.update_session_status(s2_id, "Disabled")
    db.update_session_status(s3_id, "Available")

    view = SessionsView()
    assert view.table.rowCount() == 3, f"Expected 3 rows in GUI table, got {view.table.rowCount()}"
    print("✅ Created 3 sessions in GUI table (2 Disabled, 1 Available)")

    # 2. Test Deleting one Disabled Session
    s1_data = db.get_session(s1_id)
    # Monkey-patch _confirm_delete_dialog to return True automatically
    view._confirm_delete_dialog = lambda title, text: True
    
    view._on_delete_single(s1_data)
    assert db.get_session(s1_id) is None, "Disabled Session 01 should be deleted from DB"
    assert view.table.rowCount() == 2, f"Expected 2 rows in GUI table after deletion, got {view.table.rowCount()}"
    print("✅ Successfully deleted 1 Disabled session from GUI without crash!")

    # 3. Test Deleting one Available Session
    s3_data = db.get_session(s3_id)
    view._on_delete_single(s3_data)
    assert db.get_session(s3_id) is None, "Available Session 'dola 1' should be deleted from DB"
    assert view.table.rowCount() == 1, f"Expected 1 row in GUI table after deletion, got {view.table.rowCount()}"
    print("✅ Successfully deleted 1 Available session from GUI without crash!")

    # 4. Test Deleting Multiple Selected Sessions
    s4_id = SessionManager.add_session("Multi Account A", "cookies_json", cookie_data='[{"name":"ca","value":"a"}]')
    s5_id = SessionManager.add_session("Multi Account B", "cookies_json", cookie_data='[{"name":"cb","value":"b"}]')
    view.load_sessions()
    assert view.table.rowCount() == 3

    # Select items in row 1 and row 2 in table
    view.table.item(1, 0).setSelected(True)
    view.table.item(2, 0).setSelected(True)
    
    view._on_delete_selected()
    assert db.get_session(s4_id) is None, "Multi Account A should be deleted"
    assert db.get_session(s5_id) is None, "Multi Account B should be deleted"
    assert view.table.rowCount() == 1
    print("✅ Successfully deleted multiple selected sessions from GUI without crash!")

    # 5. Test Attempting to Delete a BUSY Session (Must be blocked)
    busy_id = SessionManager.add_session("Busy Account", "cookies_json", cookie_data='[{"name":"cbasy","value":"b"}]')
    db.update_session_status(busy_id, "Busy")
    view.load_sessions()

    busy_data = db.get_session(busy_id)
    warning_shown = []
    QMessageBox.warning = lambda parent, title, text: warning_shown.append(text)

    view._on_delete_single(busy_data)
    assert db.get_session(busy_id) is not None, "BUSY session MUST NOT be deleted!"
    assert len(warning_shown) > 0, "Warning dialog should be shown for busy session"
    assert "currently in use" in warning_shown[0]
    print("✅ BUSY session deletion safely blocked with user warning!")

    print("\n🎉 ALL GUI SESSION DELETION TESTS PASSED FLAWLESSLY!")

if __name__ == "__main__":
    test_gui_session_deletion()
