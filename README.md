# FB AutoViral SaaS Pro

Modern Windows Desktop Application for Facebook Account & Reel Automation with verification-first state machine architecture.

## Milestone 1 Overview

Milestone 1 implements the application foundation:
- Modular folder structure & package layout
- CustomTkinter dark-mode desktop GUI shell with non-blocking threading
- Dedicated Playwright Desktop Chromium Browser Manager
- Configurable physical browser window (e.g. 400x400 debug mode, user resizable/draggable)
- Debug Mode toggle (headless=False visible window + slow_mo delay)
- Persistent browser session & profile storage foundation (`data/accounts/{account_id}/`)
- Thread-safe structured logging & live log streaming panel
- Error screenshot capture utility
- SQLite database layer using Python standard library `sqlite3`

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright Chromium browser binaries:
```bash
python -m playwright install chromium
```

## Running the Application

Launch the desktop GUI:
```bash
python main.py
```

## Running Independent Browser Launch Test

To test the Playwright Chromium browser launch independently:
```bash
python tests/test_browser.py
```
