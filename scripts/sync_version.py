"""
Stamps one version number across every place the project declares it.

Called by the GitHub Actions build with the version taken from the pushed tag
(v2.1.2 -> 2.1.2), and usable locally:

    python scripts/sync_version.py 2.1.2
    python scripts/sync_version.py            # just prints current values
"""

import json
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

VERSION_FILE = ROOT_DIR / "data" / "app_version.txt"
UPDATER_FILE = ROOT_DIR / "app" / "core" / "updater.py"
RELEASE_ZIP_FILE = ROOT_DIR / "scripts" / "upload_release_zip.py"
TAURI_CONF = ROOT_DIR / "src-tauri" / "tauri.conf.json"
CARGO_TOML = ROOT_DIR / "src-tauri" / "Cargo.toml"
CARGO_LOCK = ROOT_DIR / "src-tauri" / "Cargo.lock"

CRATE_NAME = "waqas-automation-pro"

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"  updated {path.relative_to(ROOT_DIR)}")


def current_versions() -> dict:
    out = {}
    if VERSION_FILE.exists():
        out["data/app_version.txt"] = _read(VERSION_FILE).strip()
    if UPDATER_FILE.exists():
        m = re.search(r'CURRENT_VERSION\s*=\s*"([^"]+)"', _read(UPDATER_FILE))
        out["updater.CURRENT_VERSION"] = m.group(1) if m else "?"
    if RELEASE_ZIP_FILE.exists():
        m = re.search(r'RELEASE_VERSION\s*=\s*"([^"]+)"', _read(RELEASE_ZIP_FILE))
        out["upload_release_zip.RELEASE_VERSION"] = m.group(1) if m else "?"
    if TAURI_CONF.exists():
        out["tauri.conf.json"] = json.loads(_read(TAURI_CONF)).get("version", "?")
    if CARGO_TOML.exists():
        m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', _read(CARGO_TOML))
        out["Cargo.toml"] = m.group(1) if m else "?"
    if CARGO_LOCK.exists():
        m = re.search(
            r'name = "%s"\nversion = "([^"]+)"' % re.escape(CRATE_NAME),
            _read(CARGO_LOCK),
        )
        out["Cargo.lock"] = m.group(1) if m else "?"
    return out


def apply(version: str) -> None:
    print(f"[sync_version] Stamping v{version} ...")

    VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    _write(VERSION_FILE, version)

    text = _read(UPDATER_FILE)
    new_text = re.sub(r'CURRENT_VERSION\s*=\s*"[^"]+"', f'CURRENT_VERSION = "{version}"', text, count=1)
    if new_text != text:
        _write(UPDATER_FILE, new_text)

    if RELEASE_ZIP_FILE.exists():
        text = _read(RELEASE_ZIP_FILE)
        new_text = re.sub(r'RELEASE_VERSION\s*=\s*"[^"]+"', f'RELEASE_VERSION = "{version}"', text, count=1)
        if new_text != text:
            _write(RELEASE_ZIP_FILE, new_text)

    conf = json.loads(_read(TAURI_CONF))
    conf["version"] = version
    for window in conf.get("app", {}).get("windows", []):
        if "title" in window:
            window["title"] = re.sub(r"v\d+\.\d+\.\d+", f"v{version}", window["title"])
    _write(TAURI_CONF, json.dumps(conf, indent=2) + "\n")

    text = _read(CARGO_TOML)
    new_text = re.sub(r'(?m)^version\s*=\s*"[^"]+"', f'version = "{version}"', text, count=1)
    if new_text != text:
        _write(CARGO_TOML, new_text)

    # Keep the lockfile in step so `cargo build --locked` never trips over it.
    if CARGO_LOCK.exists():
        text = _read(CARGO_LOCK)
        new_text = re.sub(
            r'(name = "%s"\nversion = )"[^"]+"' % re.escape(CRATE_NAME),
            lambda m: f'{m.group(1)}"{version}"',
            text,
            count=1,
        )
        if new_text != text:
            _write(CARGO_LOCK, new_text)


def main() -> int:
    if len(sys.argv) < 2:
        print("[sync_version] Current declared versions:")
        for key, value in current_versions().items():
            print(f"  {key:38} {value}")
        return 0

    version = sys.argv[1].strip().lstrip("vV")
    if not SEMVER_RE.match(version):
        print(f"[ERROR] '{version}' is not a MAJOR.MINOR.PATCH version.")
        return 1

    apply(version)
    print("[sync_version] Done. Values now:")
    for key, value in current_versions().items():
        print(f"  {key:38} {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
