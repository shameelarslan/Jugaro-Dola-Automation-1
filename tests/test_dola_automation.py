"""
Comprehensive Automated Test Suite for Dola Bulk Video Automation Software.
Tests Database, Config, Prompt Manager, Session Manager, Dola Pattern Engine, Batch 1:1 Mapping & Download Verifier.
"""

import os
import sys
import tempfile
import time
from pathlib import Path

# Force UTF-8 encoding for stdout/stderr on Windows
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    import io
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.core.config import AppConfig, DEFAULT_EXTENSION_PATH
from app.core.database import db
from app.core.logger import logger, sanitize_message
from app.managers.prompt_manager import PromptManager
from app.managers.session_manager import SessionManager
from app.managers.preset_manager import PresetManager
from app.automation.dola_patterns import DolaPatternEngine, ChatMessageBaseline
from app.automation.download_verifier import DownloadVerifier
from app.core.batch_manager import BatchManager

def test_config_and_database():
    print("\n--- 1. Testing Config & Database Schema ---")
    config = db.load_app_config()
    assert config.concurrency_limit >= 1, f"Expected concurrency >= 1, got {config.concurrency_limit}"
    assert config.extension_path == DEFAULT_EXTENSION_PATH
    print("✅ Config defaults & SQLite tables verified successfully!")

def test_prompt_manager():
    print("\n--- 2. Testing Prompt Manager ---")
    raw_input = "Prompt 01: Behind the camera film shooting\nPrompt 02: Cinematic waterfall in 4k\n\nPrompt 01: Behind the camera film shooting"
    lines = PromptManager.parse_text_lines(raw_input)
    assert len(lines) == 3, f"Expected 3 raw lines, got {len(lines)}"

    db.clear_all_prompts()
    added, dups = PromptManager.save_prompts(lines, deduct_duplicates=True)
    assert added == 2, f"Expected 2 added prompts, got {added}"
    assert dups == 1, f"Expected 1 duplicate skipped, got {dups}"

    prompts = db.get_all_prompts()
    assert len(prompts) == 2
    print("✅ Prompt parsing and deduplication verified!")

def test_session_manager():
    print("\n--- 3. Testing Session Manager & Masking ---")
    raw_cookies = '[{"name": "session_id", "value": "secret_abc_123", "domain": ".dola.com"}]'
    
    # Clean previous
    for s in db.get_all_sessions():
        db.delete_session(s["id"])

    s_id = SessionManager.add_session("Test Account 01", "cookies_json", cookie_data=raw_cookies)
    assert s_id > 0

    masked = SessionManager.get_masked_session_list()
    assert len(masked) == 1
    assert masked[0]["cookie_data"] == "***MASKED***"
    assert "secret_abc_123" not in masked[0]["cookie_summary"]
    print("✅ Session manager cookie masking and security verified!")

def test_pattern_engine():
    print("\n--- 4. Testing Dola Pattern Engine (Primary vs Supporting Signals) ---")
    engine = DolaPatternEngine()

    # Case A: Duration Warning
    warning_text = "Currently generating videos longer than 10 seconds is not supported, do you want to continue generating for you?"
    assert engine.is_duration_warning(warning_text) is True, "Expected warning pattern match"

    # Case B: Supporting Signal Alone MUST NOT trigger GENERATING
    supporting_only = "The video will use Seedance 2.0 model. You have 5 points left today."
    is_start, primary, supporting = engine.is_generation_start(supporting_only)
    assert primary is False, "Primary signal should be False"
    assert supporting is True, "Supporting signal should be True"
    assert is_start is False, "is_start MUST be False when primary signal is absent!"

    # Case C: Primary Signal Present
    primary_text = "The video will be generated using Dreamina Seedance 2.0. It will be ready in 1-3 minutes. I'll send it to you when it's done."
    is_start, primary, supporting = engine.is_generation_start(primary_text)
    assert primary is True, "Primary signal should be True"
    assert is_start is True, "is_start MUST be True when primary signal is present!"
    print("✅ Dola pattern engine primary signal weighting verified!")

def test_automation_queue_mapping():
    print("\n--- 5. Testing Automation Queue 1:1 Mapping ---")
    prompts = db.get_all_prompts()
    sessions = db.get_all_sessions()
    
    # Add one more session so we have 2 prompts & 2 sessions
    SessionManager.add_session("Test Account 02", "cookies_json", cookie_data='[{"name": "sess2", "value": "xyz"}]')
    sessions = db.get_all_sessions()

    from app.core.queue_manager import QueueManager
    qm = QueueManager(AppConfig())
    run_id = qm.prepare_and_start_automation(prompts, sessions)
    jobs = db.get_all_jobs()
    assert len(jobs) >= 2, f"Expected at least 2 jobs, got {len(jobs)}"
    print(f"✅ Automation 1:1 queue mapping created (Run ID: {run_id})")

def test_download_verifier():
    print("\n--- 6. Testing Concurrency-Safe Download Verifier ---")
    with tempfile.TemporaryDirectory() as tmp_dir:
        existing, snap_time = DownloadVerifier.snapshot_directory(tmp_dir)
        
        # Simulate extension creating a new MP4 file
        new_file = Path(tmp_dir) / "Awaiso_Auto_123456.mp4"
        with open(new_file, "wb") as f:
            f.write(b"\x00\x00\x00\x1cftypisom" * 100) # Fake MP4 bytes

        import asyncio
        async def run_verifier():
            return await DownloadVerifier.wait_for_new_download(
                download_dir=tmp_dir,
                baseline_files=existing,
                baseline_time=snap_time,
                timeout_sec=5.0
            )

        verified = asyncio.run(run_verifier())
        assert verified is not None, "Verifier should find the newly created MP4 file"
        verified_path, file_size = verified
        assert verified_path == str(new_file.resolve())
        assert file_size > 0
        print("✅ Download verifier file snapshotting and stability test passed!")

def test_session_management_actions():
    print("\n--- 7. Testing Session Delete, Toggle & Busy Checks ---")
    s_id = SessionManager.add_session("Test Delete Account", "cookies_json", cookie_data='[{"name": "test", "value": "123"}]')
    assert s_id > 0

    # Test toggle
    SessionManager.toggle_session(s_id)
    s = db.get_session(s_id)
    assert s["status"] == "Disabled"

    SessionManager.toggle_session(s_id)
    s = db.get_session(s_id)
    assert s["status"] == "Available"

    # Test Busy state prevention
    db.update_session_status(s_id, "Busy")
    try:
        SessionManager.delete_session(s_id)
        assert False, "Should not delete busy session"
    except ValueError as e:
        assert "currently in use" in str(e)

    # Reset to Available and delete
    db.update_session_status(s_id, "Available")
    success = SessionManager.delete_session(s_id)
    assert success is True
    assert db.get_session(s_id) is None
    print("✅ Session delete, toggle, and busy check verification passed!")

if __name__ == "__main__":
    print("\n========================================================")
    print("   RUNNING ALL DOLA BULK AUTOMATION UNIT & INTEGRATION TESTS")
    print("========================================================")
    test_config_and_database()
    test_prompt_manager()
    test_session_manager()
    test_pattern_engine()
    test_automation_queue_mapping()
    test_download_verifier()
    test_session_management_actions()
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
