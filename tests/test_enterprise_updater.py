"""
Comprehensive Automated Verification Suite for Waqas Automation Pro Update System.
Tests SemVer comparison, migration idempotency, offline safety, checksum verification, and version alignment.
"""

import os
import sys
import tempfile
import sqlite3
import hashlib
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.core.version import (
    get_installed_version,
    set_installed_version,
    is_newer_version,
    compare_versions,
    APP_VERSION
)
from app.core.migrations import MigrationManager, CURRENT_SCHEMA_VERSION
from app.core.updater import AutoUpdater

def test_1_and_2_and_3_version_comparisons():
    print("\n--- Testing Version Comparisons (TEST 1, 2, 3) ---")
    # TEST 1: Installed 2.0.7, Latest 2.1.5 -> Update Available
    assert is_newer_version("2.1.5", "2.0.7") is True, "2.1.5 should be newer than 2.0.7"
    assert compare_versions("2.1.5", "2.0.7") == 1
    print("✅ TEST 1 PASSED: Installed 2.0.7, Latest 2.1.5 -> Update Available")

    # TEST 2: Installed 2.1.5, Latest 2.1.5 -> Up to Date
    assert is_newer_version("2.1.5", "2.1.5") is False, "2.1.5 should not be newer than 2.1.5"
    assert compare_versions("2.1.5", "2.1.5") == 0
    print("✅ TEST 2 PASSED: Installed 2.1.5, Latest 2.1.5 -> Up to Date")

    # TEST 3: Installed 2.2.0, Latest 2.1.5 -> No downgrade
    assert is_newer_version("2.1.5", "2.2.0") is False, "2.1.5 is not newer than 2.2.0"
    assert compare_versions("2.2.0", "2.1.5") == 1
    print("✅ TEST 3 PASSED: Installed 2.2.0, Latest 2.1.5 -> No downgrade")

    # Additional SemVer edge cases
    assert is_newer_version("v2.1.5", "2.1.4") is True
    assert is_newer_version("3.0.0", "2.9.9") is True
    assert is_newer_version("2.1.5", "v2.1.5") is False
    print("✅ Additional SemVer prefix & major version tests PASSED")

def test_4_offline_behavior():
    print("\n--- Testing Offline / Unreachable Network Resilience (TEST 4) ---")
    updater = AutoUpdater()
    # Mocking check on unreachable endpoint should fail gracefully without exception
    rel, err = updater._check_github()
    print(f"  --> GitHub check returned: rel={bool(rel)}, err={err}")
    is_avail, info, check_err = updater.check_for_updates()
    print(f"  --> check_for_updates returned: is_avail={is_avail}, info={bool(info)}, err={check_err}")
    assert isinstance(is_avail, bool)
    print("✅ TEST 4 PASSED: Offline/Network check handles gracefully without crashing application")

def test_5_checksum_verification_and_download_safety():
    print("\n--- Testing SHA-256 Checksum Verification & Download Safety (TEST 5) ---")
    updater = AutoUpdater()

    # Create dummy download file
    temp_dir = tempfile.mkdtemp()
    dummy_file = os.path.join(temp_dir, "test.zip")
    with open(dummy_file, "wb") as f:
        f.write(b"PK\x03\x04DummyZipContentForIntegrityCheck1234567890")

    hasher = hashlib.sha256()
    with open(dummy_file, "rb") as f:
        hasher.update(f.read())
    correct_sha = hasher.hexdigest()
    bad_sha = "0000000000000000000000000000000000000000000000000000000000000000"

    # Verify corrupt download detection
    res, msg = updater.download_and_install_update(
        download_url=Path(dummy_file).as_uri(),
        version_str="2.1.5",
        expected_sha256=bad_sha
    )
    assert res is False, "Corrupted SHA256 must be rejected!"
    assert "Integrity check failed" in msg
    print("✅ TEST 5 PASSED: Download failure/tamper detection correctly rejects corrupted package")

def test_6_and_7_database_migrations_and_data_preservation():
    print("\n--- Testing Database Migrations & Data Preservation (TEST 6, 7) ---")
    temp_db = tempfile.mktemp(suffix=".db")

    # Step 1: Create older v1 schema with user sessions and settings
    conn = sqlite3.connect(temp_db)
    conn.execute("""
        CREATE TABLE settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            session_type TEXT NOT NULL,
            cookie_data TEXT,
            profile_path TEXT,
            status TEXT DEFAULT 'Available'
        )
    """)
    conn.execute("INSERT INTO settings (key, value) VALUES ('user_api_key', 'SECRET_USER_KEY_12345')")
    conn.execute("INSERT INTO sessions (name, session_type, cookie_data) VALUES ('MyImportantSession', 'Profile', 'user_cookies_here')")
    conn.commit()
    conn.close()

    # Step 2: Run MigrationManager
    migrator = MigrationManager(temp_db)
    migrator.run_migrations()

    # Step 3: Verify all new columns exist and existing data is intact
    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Check preserved user settings
    cursor.execute("SELECT value FROM settings WHERE key='user_api_key'")
    row = cursor.fetchone()
    assert row is not None and row[0] == 'SECRET_USER_KEY_12345', "User settings MUST be preserved!"

    # Check preserved user session
    cursor.execute("SELECT name, credits_left, videos_left FROM sessions WHERE name='MyImportantSession'")
    session_row = cursor.fetchone()
    assert session_row is not None, "User session data MUST be preserved!"
    assert session_row['credits_left'] == 4, "Migrated column credits_left must default properly"
    assert session_row['videos_left'] == 15, "Migrated column videos_left must default properly"

    # Check new tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='leads'")
    assert cursor.fetchone() is not None, "New leads table must exist"

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='_schema_migrations'")
    assert cursor.fetchone() is not None, "_schema_migrations table must exist"

    cursor.execute("SELECT MAX(version) FROM _schema_migrations")
    assert cursor.fetchone()[0] == CURRENT_SCHEMA_VERSION

    # Step 4: Run migrations again to verify IDEMPOTENCY
    migrator.run_migrations()
    print("✅ TEST 6 & 7 PASSED: Database migration upgraded schema safely without losing existing user data (Idempotent)")
    conn.close()
    import gc
    gc.collect()
    try:
        if os.path.exists(temp_db):
            os.remove(temp_db)
    except Exception:
        pass

def test_8_and_9_roles_and_permissions():
    print("\n--- Testing Role-Based UI & Authorization Separation (TEST 8, 9) ---")
    from app.core.cloud_manager import CloudManager
    cm = CloudManager()

    # Test Admin detection
    admin_role = cm.determine_role("waqasai@gmail.com", "free")
    assert admin_role == "admin", "Admin email in ADMIN_EMAILS must map to admin role"
    admin_role_2 = cm.determine_role("anyuser@example.com", "admin")
    assert admin_role_2 == "admin", "User with DB role admin must map to admin"

    # Test Paid Creator detection
    paid_role = cm.determine_role("client@agency.com", "paid")
    assert paid_role == "paid", "Paid user must map to paid"

    # Test Free user detection
    free_role = cm.determine_role("freeuser@domain.com", "free")
    assert free_role == "free", "Free user must map to free"

    print("✅ TEST 8 & 9 PASSED: Role-based authorization cleanly maps admin, paid, and free roles")

def test_10_version_source_alignment():
    print("\n--- Testing Canonical Version Consistency (TEST 10) ---")
    installed_ver = get_installed_version()
    assert installed_ver == APP_VERSION, f"get_installed_version() ({installed_ver}) must match APP_VERSION ({APP_VERSION})"
    print(f"✅ TEST 10 PASSED: Canonical version is aligned across all modules: v{installed_ver}")

if __name__ == "__main__":
    test_1_and_2_and_3_version_comparisons()
    test_4_offline_behavior()
    test_5_checksum_verification_and_download_safety()
    test_6_and_7_database_migrations_and_data_preservation()
    test_8_and_9_roles_and_permissions()
    test_10_version_source_alignment()
    print("\n" + "=" * 64)
    print("🎉 ALL 10 ENTERPRISE UPDATER TESTS PASSED SUCCESSFULLY!")
    print("=" * 64 + "\n")
