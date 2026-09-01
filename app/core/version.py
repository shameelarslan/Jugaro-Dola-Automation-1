"""
Single Canonical Source of Truth for Application Version.
Waqas Automation Pro - Unified Version Management System.
"""

import sys
from pathlib import Path
from packaging import version as pkg_version
from typing import Tuple

# Current Base Application Version (Updated during release pipeline)
APP_VERSION = "2.1.5"
APP_NAME = "Waqas Automation Pro"

def get_base_dir() -> Path:
    """Returns application root directory (works in both frozen and dev environments)."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent

def get_data_dir() -> Path:
    """Returns persistent data directory."""
    d = get_base_dir() / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_version_file_path() -> Path:
    """Returns path to app_version.txt."""
    return get_data_dir() / "app_version.txt"

def get_installed_version() -> str:
    """
    Reads the installed version from data/app_version.txt.
    If the file does not exist or has an older string than codebase APP_VERSION,
    it synchronizes with APP_VERSION.
    """
    v_file = get_version_file_path()
    if v_file.exists():
        try:
            v_text = v_file.read_text(encoding="utf-8").strip()
            if v_text:
                # If code version is newer than stored version, sync it
                if is_newer_version(APP_VERSION, v_text):
                    set_installed_version(APP_VERSION)
                    return APP_VERSION
                return v_text
        except Exception:
            pass
    set_installed_version(APP_VERSION)
    return APP_VERSION

def set_installed_version(ver: str):
    """Persists updated version string to disk safely."""
    try:
        v_file = get_version_file_path()
        v_file.parent.mkdir(parents=True, exist_ok=True)
        v_file.write_text(ver.strip(), encoding="utf-8")
        
        # In frozen app, also sync to _internal/data if it exists
        if getattr(sys, 'frozen', False):
            internal_v_file = get_base_dir() / "_internal" / "data" / "app_version.txt"
            if internal_v_file.parent.exists():
                internal_v_file.write_text(ver.strip(), encoding="utf-8")
    except Exception:
        pass

def is_newer_version(candidate: str, reference: str) -> bool:
    """
    Returns True if candidate is strictly newer than reference according to Semantic Versioning.
    Handles 'v2.1.5' vs '2.1.5' seamlessly.
    """
    c_clean = candidate.strip().lstrip("vV")
    r_clean = reference.strip().lstrip("vV")
    try:
        return pkg_version.parse(c_clean) > pkg_version.parse(r_clean)
    except Exception:
        try:
            c_parts = [int(p) for p in c_clean.split(".") if p.isdigit()]
            r_parts = [int(p) for p in r_clean.split(".") if p.isdigit()]
            return c_parts > r_parts
        except Exception:
            return False

def compare_versions(v1: str, v2: str) -> int:
    """
    Compares two versions:
    returns 1 if v1 > v2, 0 if v1 == v2, -1 if v1 < v2.
    """
    v1_clean = v1.strip().lstrip("vV")
    v2_clean = v2.strip().lstrip("vV")
    try:
        p1 = pkg_version.parse(v1_clean)
        p2 = pkg_version.parse(v2_clean)
        if p1 > p2:
            return 1
        elif p1 < p2:
            return -1
        return 0
    except Exception:
        if v1_clean == v2_clean:
            return 0
        return 1 if is_newer_version(v1_clean, v2_clean) else -1
