"""
Playwright Chromium Launcher with Native Window Viewport & Pure Native Download Handling.
Operates 100% natively without external extension dependencies.
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
    async def create_browser_context(
        playwright: Playwright,
        session_info: Dict[str, Any],
        extension_path: str = "",
        headless: bool = False,
        user_data_dir: Optional[str] = None,
        output_folder: Optional[str] = None
    ) -> Tuple[BrowserContext, Page]:
        """
        Launches an isolated native Playwright Chromium instance.
        Uses no_viewport=True and viewport=None so Chromium scales 100% natively.
        Includes automated download handling directly to output_folder.
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

        # --- Determine profile dir ---
        session_type = session_info.get("session_type", "cookies_json")
        if session_type == "profile_dir" and session_info.get("profile_path"):
            profile_dir = session_info["profile_path"]
        else:
            profile_dir = user_data_dir or tempfile.mkdtemp(
                prefix=f"dola_session_{session_info.get('id', 0)}_"
            )

        logger.info(
            f"Launching Chromium context (Profile: {profile_dir}, Viewport: Native Full Window, Pure Native Engine)",
            category="BROWSER"
        )

        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=headless,
            viewport=None,
            no_viewport=True, # Officially disables Playwright viewport emulation for full native scroll
            args=chrome_args,
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
                cookies = json.loads(session_info["cookie_data"])
                if isinstance(cookies, dict):
                    cookies = [cookies]
                valid_cookies = []
                for c in cookies:
                    if isinstance(c, dict) and "name" in c and "value" in c:
                        c_dict = {
                            "name": str(c["name"]),
                            "value": str(c["value"]),
                            "domain": str(c.get("domain", ".dola.com")),
                            "path": str(c.get("path", "/")),
                            "secure": bool(c.get("secure", True)),
                        }
                        if "expires" in c:
                            c_dict["expires"] = float(c["expires"])
                        valid_cookies.append(c_dict)

                await context.add_cookies(valid_cookies)
                logger.info(f"Injected {len(valid_cookies)} cookies for session '{session_info.get('name')}'", category="BROWSER")
            except Exception as e:
                logger.error(f"Error injecting cookies for session '{session_info.get('name')}': {e}", category="BROWSER")

        page = context.pages[0] if context.pages else await context.new_page()
        return context, page
