"""
Playwright Chromium Launcher with Native Window Viewport & Pure Native Download Handling.
Features Zero-Dependency System Browser Auto-Detection (Chrome / Edge / Brave / Chromium).
Runs on any Windows machine out-of-the-box without requiring 'playwright install'.
"""

import os
import json
import asyncio
import tempfile
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from playwright.async_api import async_playwright, Playwright, BrowserContext, Page, Download
from app.core.logger import logger

class BrowserFactory:
    @staticmethod
    def get_system_browser() -> Tuple[Optional[str], Optional[str]]:
        """
        Locates the best available Chromium-based browser on the host system.
        PRIORITY: Playwright bundled Chromium > System Chrome > Edge > Brave
        Using bundled Chromium first avoids conflicts with user's personal browser sessions.
        Returns: (executable_path, channel)
        """
        # 1. PRIORITY: Check Playwright bundled Chromium in AppData (isolated, no conflict)
        playwright_cache = os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright")
        if os.path.isdir(playwright_cache):
            for root, dirs, files in os.walk(playwright_cache):
                if "chrome.exe" in files:
                    return os.path.join(root, "chrome.exe"), None

        # 2. Standard Google Chrome paths (fallback if bundled not available)
        chrome_candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
        ]
        for p in chrome_candidates:
            if os.path.isfile(p):
                return p, "chrome"

        # 3. Standard Microsoft Edge paths
        edge_candidates = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
        ]
        for p in edge_candidates:
            if os.path.isfile(p):
                return p, "msedge"

        # 4. Brave Browser
        brave_candidates = [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ]
        for p in brave_candidates:
            if os.path.isfile(p):
                return p, None

        # Fallback to standard Playwright channel names
        return None, "chrome"

    @staticmethod
    async def create_browser_context(
        playwright: Playwright,
        session_info: Dict[str, Any],
        extension_path: str = "",
        headless: bool = False,
        user_data_dir: Optional[str] = None,
        output_folder: Optional[str] = None
    ) -> Tuple[BrowserContext, Page]:
        """
        Launches an isolated Playwright Chromium browser + context (non-persistent).
        Uses browser.launch() + browser.new_context() to avoid profile dir locking.
        Each call creates a fresh, fully independent browser window.
        """
        # --- Build Chrome args (Optimized for Low-RAM / High Stability) ---
        chrome_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--start-maximized",
            "--renderer-process-limit=2",
            "--js-flags=--max-old-space-size=256",
            "--disable-dev-shm-usage",
            "--disable-background-networking",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-breakpad",
            "--disable-component-update",
            "--disable-default-apps",
            "--disable-domain-reliability",
            "--disable-sync",
            "--disable-translate",
            "--no-first-run",
            "--no-default-browser-check",
            "--memory-pressure-off",
        ]

        session_type = session_info.get("session_type", "cookies_json")

        # Resolve system browser executable
        exec_path, channel = BrowserFactory.get_system_browser()

        logger.info(
            f"Launching Chromium browser (Session: {session_info.get('name')}, Engine: {exec_path or channel or 'default'})",
            category="BROWSER"
        )

        # --- Launch browser (non-persistent — no profile dir lock) ---
        launch_kwargs = {
            "headless": headless,
            "args": chrome_args,
        }

        if exec_path:
            launch_kwargs["executable_path"] = exec_path
        elif channel:
            launch_kwargs["channel"] = channel

        browser = None
        for attempt_label, attempt_kwargs in [
            (f"primary ({exec_path or channel})", dict(launch_kwargs)),
            ("Edge fallback", {**{k: v for k, v in launch_kwargs.items() if k != "executable_path"}, "channel": "msedge"}),
            ("Chrome channel", {**{k: v for k, v in launch_kwargs.items() if k != "executable_path"}, "channel": "chrome"}),
            ("bundled chromium", {k: v for k, v in launch_kwargs.items() if k not in ("executable_path", "channel")}),
        ]:
            try:
                browser = await playwright.chromium.launch(**attempt_kwargs)
                break
            except Exception as e:
                logger.warning(f"Browser launch failed ({attempt_label}): {e}", category="BROWSER")

        if not browser:
            raise RuntimeError("Failed to launch any Chromium browser. Please install Chrome, Edge, or run 'playwright install chromium'.")

        # --- Create isolated context ---
        context = await browser.new_context(
            viewport=None,
            no_viewport=True,
            accept_downloads=True,
        )

        # Inject CSS init script to ensure HTML, Body & main containers allow vertical scrolling
        try:
            await context.add_init_script("""() => {
                const injectScrollFix = () => {
                    if (!document.getElementById('dola-scroll-fix')) {
                        const style = document.createElement('style');
                        style.id = 'dola-scroll-fix';
                        style.innerHTML = `
                            html, body, #__next, main, div[role="main"], div.chat-container, div.messages-container {
                                overflow-y: auto !important;
                                scroll-behavior: smooth !important;
                            }
                        `;
                        (document.head || document.documentElement).appendChild(style);
                    }
                };
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', injectScrollFix);
                } else {
                    injectScrollFix();
                }
            }""")
        except Exception:
            pass

        # --- Register Playwright native download-intercept fallback ---
        if output_folder:
            os.makedirs(output_folder, exist_ok=True)

            async def _on_download(download: Download) -> None:
                if getattr(download.page, "_job_completed", False):
                    return
                filename = download.suggested_filename or f"dola_video_{int(asyncio.get_event_loop().time())}.mp4"
                dest = str(Path(output_folder) / filename)
                try:
                    await download.save_as(dest)
                    logger.info(
                        f"[DOWNLOAD INTERCEPT] Saved: {dest}",
                        category="BROWSER"
                    )
                except Exception as e:
                    logger.error(
                        f"[DOWNLOAD INTERCEPT] Failed to save {filename}: {e}",
                        category="BROWSER"
                    )

            context.on("download", _on_download)

        # --- Inject session cookies ---
        if session_type == "cookies_json" and session_info.get("cookie_data"):
            try:
                raw_cookie_data = str(session_info["cookie_data"]).strip()
                cookies = []
                if raw_cookie_data.startswith("[") or raw_cookie_data.startswith("{"):
                    try:
                        parsed = json.loads(raw_cookie_data)
                        cookies = parsed if isinstance(parsed, list) else [parsed]
                    except Exception:
                        pass
                
                # Fallback parser for Netscape / Header style cookie string
                if not cookies and raw_cookie_data:
                    for line in raw_cookie_data.splitlines():
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        parts = line.split("\t")
                        if len(parts) >= 7:
                            try:
                                cookies.append({
                                    "domain": parts[0],
                                    "path": parts[2],
                                    "secure": parts[3].lower() == "true",
                                    "expires": float(parts[4]) if parts[4].replace(".", "", 1).isdigit() else None,
                                    "name": parts[5],
                                    "value": parts[6]
                                })
                            except Exception:
                                pass
                        elif "=" in line:
                            for pair in line.split(";"):
                                if "=" in pair:
                                    k, v = pair.strip().split("=", 1)
                                    cookies.append({"name": k.strip(), "value": v.strip(), "domain": ".dola.com", "path": "/"})

                # sameSite normalization map for Chrome extension export formats
                SAME_SITE_MAP = {
                    "strict": "Strict",
                    "lax": "Lax",
                    "none": "None",
                    "no_restriction": "None",   # Chrome extension uses this for SameSite=None
                    "unspecified": "Lax",        # Chrome extension default → treat as Lax
                }

                valid_cookies = []
                seen = set()  # deduplicate by (name, domain, path)
                
                for c in cookies:
                    if not isinstance(c, dict) or "name" not in c or "value" not in c:
                        continue
                    
                    name = str(c["name"]).strip()
                    value = str(c["value"]).strip()
                    if not name or not value:
                        continue

                    # --- Domain normalization ---
                    domain = str(c.get("domain", "")).strip()
                    host_only = c.get("hostOnly", False)
                    
                    if not domain:
                        domain = ".dola.com"
                    
                    # For hostOnly cookies exported from Chrome, domain must NOT have leading dot
                    # For non-hostOnly cookies, domain SHOULD have leading dot for subdomain coverage
                    if host_only:
                        domain = domain.lstrip(".")
                    else:
                        if not domain.startswith("."):
                            domain = f".{domain}"

                    path = str(c.get("path", "/")).strip() or "/"
                    secure = bool(c.get("secure", False))
                    http_only = bool(c.get("httpOnly", False))

                    # --- sameSite normalization ---
                    raw_ss = str(c.get("sameSite", "unspecified")).lower().strip()
                    same_site = SAME_SITE_MAP.get(raw_ss, "Lax")
                    
                    # SameSite=None requires Secure=true per browser spec
                    if same_site == "None":
                        secure = True

                    # --- expires: handle both "expires" and "expirationDate" fields ---
                    expires_val = c.get("expires") or c.get("expirationDate")
                    expires = None
                    if expires_val is not None:
                        try:
                            expires = float(expires_val)
                            # Skip already-expired cookies (timestamp in the past)
                            import time
                            if expires > 0 and expires < time.time():
                                continue
                        except (ValueError, TypeError):
                            pass

                    # Deduplicate
                    key = (name, domain, path)
                    if key in seen:
                        continue
                    seen.add(key)

                    c_dict = {
                        "name": name,
                        "value": value,
                        "domain": domain,
                        "path": path,
                        "secure": secure,
                        "httpOnly": http_only,
                        "sameSite": same_site,
                    }
                    if expires is not None and expires > 0:
                        c_dict["expires"] = expires
                    
                    valid_cookies.append(c_dict)

                if valid_cookies:
                    await context.add_cookies(valid_cookies)
                    logger.info(f"Injected {len(valid_cookies)} cookies for session '{session_info.get('name')}'", category="BROWSER")
                else:
                    logger.warning(f"No valid cookies found for session '{session_info.get('name')}'", category="BROWSER")
            except Exception as e:
                logger.error(f"Error injecting cookies for session '{session_info.get('name')}': {e}", category="BROWSER")

        page = context.pages[0] if context.pages else await context.new_page()
        
        # Store browser reference on context so it can be closed later
        context._browser_instance = browser
        
        return context, page
