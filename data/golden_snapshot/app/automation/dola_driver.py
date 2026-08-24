"""
Dola.com UI Automation Driver.
Handles UI interactions, form filling, model selection, scoped response scanning, auto-confirmation, and reload triggers.
"""

import os
import time
import asyncio
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List, Set
from playwright.async_api import Page
from app.automation.dola_selectors import DolaSelectors
from app.automation.dola_patterns import DolaPatternEngine, ChatMessageBaseline
from app.core.logger import logger

class DolaDriver:
    def __init__(self, page: Page, worker_id: Optional[int] = None, job_id: Optional[str] = None):
        self.page = page
        self.worker_id = worker_id
        self.job_id = job_id
        self.pattern_engine = DolaPatternEngine()
        self.output_folder = ""
        self.captured_video_files = []
        self.job_completed = False
        self.processed_urls = set()

    def setup_network_media_interceptor(self, output_folder: str):
        """
        Attaches a real-time Playwright response listener to intercept raw .mp4, video streams, or JSON play info
        as Dola loads or buffers the video on the page, saving directly to disk.
        """
        self.output_folder = output_folder
        if not hasattr(self, "captured_video_files"):
            self.captured_video_files = []
        if not hasattr(self, "captured_video_urls"):
            self.captured_video_urls = []

        async def _on_response(response):
            if getattr(self, "job_completed", False):
                return
            try:
                url = response.url
                if url in self.processed_urls:
                    return
                lower_url = url.lower()
                headers = response.headers
                content_type = headers.get("content-type", "").lower()

                # Ignore non-media static assets unless they contain explicit video endpoint keys
                invalid_exts = ['.js', '.css', '.png', '.jpg', '.jpeg', '.svg', '.woff', '.woff2', '.gif', '.ico', '.map', '.wasm']
                if any(lower_url.endswith(ext) or (ext + '?') in lower_url for ext in invalid_exts):
                    if not any(k in lower_url for k in ['/get_play_info', '/video/', 'video_mp4', 'mime_type=video_mp4']):
                        return

                # Detect valid media/video requests
                is_media_req = (
                    "/get_play_info" in lower_url or
                    "/video/" in lower_url or
                    "/videos/" in lower_url or
                    ".mp4" in lower_url or
                    "video_mp4" in lower_url or
                    "mime_type=video_mp4" in lower_url or
                    "download=true" in lower_url or
                    "video/mp4" in content_type or
                    "video/webm" in content_type or
                    "video/quicktime" in content_type
                )

                if is_media_req and response.status in [200, 206]:
                    # Case A: Binary video response
                    if "video/" in content_type or ".mp4" in lower_url or "video_mp4" in lower_url or "mime_type=video_mp4" in lower_url:
                        body = await response.body()
                        if len(body) > 10000:
                            os.makedirs(output_folder, exist_ok=True)
                            filename = f"Dola_Video_{int(time.time())}.mp4"
                            filepath = str(Path(output_folder) / filename)
                            with open(filepath, "wb") as f:
                                f.write(body)
                            logger.info(f"🎥 Network Video Intercepted & Saved: {filename} ({len(body)/1024/1024:.2f} MB)", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                            if filepath not in self.captured_video_files:
                                self.captured_video_files.append(filepath)
                            if url not in self.captured_video_urls:
                                self.captured_video_urls.append(url)

                    # Case B: JSON media response (like /get_play_info) containing play URLs
                    elif "json" in content_type or "/get_play_info" in lower_url:
                        try:
                            json_data = await response.json()
                            import json, re
                            json_str = json.dumps(json_data)
                            matches = re.findall(r'https?://[^\s\'"]+\.(?:mp4|mov|webm)[^\s\'"]*', json_str)
                            if not matches:
                                matches = re.findall(r'https?://[^\s\'"]*video[^\s\'"]*', json_str)
                            for m in matches:
                                if m not in self.captured_video_urls:
                                    logger.info(f"🎥 Discovered video URL from network JSON response: {m[:80]}...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                                    self.captured_video_urls.append(m)
                                    # Trigger direct download helper asynchronously
                                    loop = asyncio.get_event_loop()
                                    loop.run_in_executor(None, self._download_url_to_folder, m, output_folder)
                        except Exception:
                            pass
            except Exception:
                pass

        try:
            self.page.on("response", lambda resp: asyncio.create_task(_on_response(resp)))
        except Exception:
            pass

    def _download_url_to_folder(self, url: str, folder: str) -> Optional[str]:
        try:
            import urllib.request
            os.makedirs(folder, exist_ok=True)
            filename = f"Dola_Video_{int(time.time())}.mp4"
            dest_path = str(Path(folder) / filename)
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            if len(data) > 10000:
                with open(dest_path, "wb") as f:
                    f.write(data)
                logger.info(f"🎉 Direct HTTP video downloaded from URL: {filename} ({len(data)/1024/1024:.2f} MB)", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                if dest_path not in self.captured_video_files:
                    self.captured_video_files.append(dest_path)
                return dest_path
        except Exception as e:
            logger.warning(f"_download_url_to_folder failed for {url[:50]}: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
        return None

    async def open_dola(self, max_retries: int = 3) -> bool:
        """Navigates to Dola chat interface and waits until page and composer are fully loaded and ready."""
        urls_to_try = [
            "https://www.dola.com/chat",
            "https://dola.com/chat",
            "https://www.dola.com"
        ]

        for attempt in range(1, max_retries + 1):
            for target_url in urls_to_try:
                try:
                    logger.info(f"Navigating to {target_url}...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                    await self.page.goto(target_url, timeout=45000, wait_until="load")
                    
                    # Dismiss any cookie consent popup
                    await self._dismiss_cookie_popup()

                    # Wait for composer/editor to be present and visible
                    logger.info("Waiting for Dola chat interface to completely load and hydrate...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                    try:
                        await self.page.wait_for_selector('form, .ProseMirror, textarea, [class*="composer"], div[contenteditable="true"]', timeout=15000)
                    except Exception:
                        pass

                    # Wait 12s for React hydration, scripts and actionbar to become fully interactive
                    logger.info("⏳ Waiting 12 seconds for Dola interface and scripts to fully stabilize...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                    await self.page.wait_for_timeout(12000)
                    await self._dismiss_cookie_popup()

                    logger.info(f"✅ Page loaded and ready: {target_url}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                    return True
                except Exception as e:
                    logger.warning(f"Navigation attempt {attempt} to {target_url} failed ({e}). Retrying...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                    await asyncio.sleep(1.5)

        logger.error(f"Failed to navigate to Dola after {max_retries} retries.", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
        return False

    async def _dismiss_cookie_popup(self) -> None:
        """Clicks 'OK' on Dola's cookie consent popup — only if cookie text is visible nearby."""
        try:
            dismissed = await self.page.evaluate("""() => {
                // Strategy 1: Find element that contains cookie policy text, then find OK inside it
                const allEls = document.querySelectorAll('*');
                for (const el of allEls) {
                    const txt = (el.innerText || '').toLowerCase();
                    if (txt.includes('cookies policy') || txt.includes('cookies and similar')) {
                        // Found cookie container — look for OK button inside or nearby
                        const okBtns = el.querySelectorAll('button, a, span, div');
                        for (const btn of okBtns) {
                            const t = (btn.innerText || btn.textContent || '').trim();
                            if (t === 'OK' || t === 'Accept') {
                                const rect = btn.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) {
                                    btn.click();
                                    return `Dismissed (cookie container): "${t}"`;
                                }
                            }
                        }
                    }
                }
                // Strategy 2: fallback — any visible OK button (only if small/popup sized)
                const btns = document.querySelectorAll('button, [role="button"]');
                for (const el of btns) {
                    const t = (el.innerText || el.textContent || '').trim();
                    if (t === 'OK') {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.width < 200 && rect.height > 0 && rect.height < 60) {
                            el.click();
                            return `Dismissed (fallback): "${t}"`;
                        }
                    }
                }
                return null;
            }""")
            if dismissed:
                logger.info(f"Cookie popup dismissed: {dismissed}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                await self.page.wait_for_timeout(800)
            else:
                logger.info("No cookie popup found — OK", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
        except Exception as e:
            logger.warning(f"Cookie popup dismiss error (non-fatal): {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

    async def extract_video_url(self) -> str | None:
        """Extracts the first valid HTTP video URL from the page.
        Scans <video src>, <source src>, blob URLs, network requests, and anchor tags with .mp4.
        Returns the URL string or None if not found.
        """
        try:
            # 0. Scroll to bottom to trigger lazy-loaded media elements
            try:
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await self.page.wait_for_timeout(1000)
            except Exception:
                pass

            result = await self.page.evaluate("""() => {
                // 1. Check <video> elements
                const videos = document.querySelectorAll('video');
                for (const v of videos) {
                    const src = v.currentSrc || v.src || '';
                    if (src.startsWith('http') || src.startsWith('blob:')) {
                        return src;
                    }
                }
                // 2. Check <source> elements inside video
                const sources = document.querySelectorAll('video source, source');
                for (const s of sources) {
                    const src = s.src || '';
                    if (src.startsWith('http') || src.startsWith('blob:')) return src;
                }
                // 3. Check <a> tags with .mp4 or download
                const links = document.querySelectorAll('a[href]');
                for (const a of links) {
                    if (a.href && (a.href.includes('.mp4') || a.href.includes('video_mp4') || a.href.includes('download'))) {
                        return a.href;
                    }
                }
                // 4. Scan all elements for data-src, data-url, or src attributes
                const all = document.querySelectorAll('[data-src],[data-url],[data-video-url],[src*=".mp4"]');
                for (const el of all) {
                    const u = el.dataset.src || el.dataset.url || el.dataset.videoUrl || el.getAttribute('src') || '';
                    if (u.startsWith('http') || u.startsWith('blob:')) return u;
                }
                return null;
            }""")
            if result:
                logger.info(f"Video URL extracted: {result[:80]}...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            return result
        except Exception as e:
            logger.warning(f"extract_video_url error: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            return None

    async def click_new_chat(self) -> bool:
        """
        Clicks the 'New Chat' button in Dola sidebar to start a fresh conversation.
        Waits for the fresh chat session to completely load and stabilize.
        """
        logger.info("Clicking New Chat to start fresh conversation...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

        new_chat_selectors = [
            "a:has-text('New Chat')",
            "button:has-text('New Chat')",
            "[href*='/chat/new']",
            "a[href='/chat']",
            "div:has-text('New Chat')",
            "[aria-label='New Chat']",
            "[title='New Chat']",
            "svg[data-icon='edit']",       # pencil/edit icon often used for new chat
            "button.new-chat-btn",
        ]

        clicked = False
        for sel in new_chat_selectors:
            try:
                loc = self.page.locator(sel).first
                if await loc.is_visible(timeout=3000):
                    await loc.click()
                    logger.info(f"New Chat clicked via: {sel}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            # Fallback: navigate directly to /chat
            logger.warning("New Chat button not found via selectors — navigating to /chat directly", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            try:
                await self.page.goto("https://www.dola.com/chat", timeout=30000, wait_until="load")
            except Exception as e:
                logger.error(f"New Chat navigation fallback failed: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return False

        # Wait for fresh chat composer and actionbar to completely load
        logger.info("Waiting for fresh chat interface to stabilize...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
        try:
            await self.page.wait_for_selector('form, .ProseMirror, textarea, [class*="composer"]', timeout=12000)
        except Exception:
            pass

        logger.info("⏳ Waiting 12 seconds for fresh chat components to fully stabilize...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
        await self.page.wait_for_timeout(12000)
        await self._dismiss_cookie_popup()
        logger.info("✅ Fresh chat interface fully ready.", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
        return True

    async def verify_login(self) -> Tuple[bool, str]:
        """
        Verifies if the current Dola session is authenticated and logged in.
        Only flags logged-out state if an explicit login modal with OAuth/QR triggers is open,
        or a top-header 'Log In' button is visible without an active composer.
        Returns (is_logged_in, reason_text).
        """
        try:
            status = await self.page.evaluate("""() => {
                const bodyText = (document.body.innerText || '').toLowerCase();

                // 1. Explicit Logout Modal / Screen Triggers (Requires modal + OAuth/QR text)
                const hasLoginTitle = bodyText.includes('log in to unlock more features') || bodyText.includes('log in to dola');
                const hasOAuth = bodyText.includes('continue with google') || bodyText.includes('scan qr code');
                if (hasLoginTitle && hasOAuth) {
                    return { logged_in: false, reason: 'Dola Login Modal ("Log In to Unlock More Features") is visible' };
                }

                // 2. Top Header / Navbar "Log In" button (Only check top header bar area)
                const header = document.querySelector('header, nav, [class*="header"], [class*="topbar"], [class*="nav"]');
                if (header) {
                    const headerBtns = Array.from(header.querySelectorAll('button, a'));
                    for (const b of headerBtns) {
                        const bt = (b.innerText || '').trim().toLowerCase();
                        if (bt === 'log in' || bt === 'login' || bt === 'sign in') {
                            const rect = b.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0 && rect.top < 120) {
                                // If composer is also absent, definitely unauthenticated
                                const composer = document.querySelector('form, .ProseMirror, textarea, [class*="composer"], div[contenteditable="true"]');
                                if (!composer) {
                                    return { logged_in: false, reason: 'Header "Log In" button visible and composer absent' };
                                }
                            }
                        }
                    }
                }

                // 3. Fallback: If composer or main chat interface exists, session is authenticated
                return { logged_in: true, reason: 'Session active' };
            }""")

            is_logged_in = bool(status.get("logged_in", True))
            reason = str(status.get("reason", ""))
            return is_logged_in, reason

        except Exception as e:
            logger.warning(f"verify_login error: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            return True, "Check skipped"

    async def take_screenshot(self, label: str) -> None:
        """Saves a debug screenshot to temp folder with given label."""
        try:
            import tempfile, time as _time
            path = f"{tempfile.gettempdir()}\\dola_debug_{label}_{int(_time.time())}.png"
            await self.page.screenshot(path=path)
            logger.info(f"Screenshot saved: {path}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

    async def _js_click_button_with_text(self, *texts: str, timeout_ms: int = 3000) -> Optional[str]:
        """Uses JS to find and click the specific leaf button/element containing one of the given texts. Returns matched text or None."""
        try:
            result = await self.page.evaluate(f"""
                (texts) => {{
                    const all = Array.from(document.querySelectorAll('button, [role="button"], a, span, div, li'));
                    /* Sort elements by text length so smallest leaf element is clicked first */
                    all.sort((a, b) => (a.innerText || '').length - (b.innerText || '').length);
                    for (const el of all) {{
                        const t = (el.innerText || el.textContent || '').trim();
                        for (const target of texts) {{
                            /* Only match if exact target or short element text (< 35 chars) to prevent clicking giant container divs */
                            if (t === target || (t.toLowerCase().includes(target.toLowerCase()) && t.length < 35)) {{
                                const rect = el.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) {{
                                    el.click();
                                    return t;
                                }}
                            }}
                        }}
                    }}
                    return null;
                }}
            """, list(texts))
            return result
        except Exception:
            return None

    async def configure_video_settings(self, model: str = "Seedance 2.0", ratio: str = "9:16", duration: int = 10) -> bool:
        """Configures video generation parameters (Create Video mode + 9:16 ratio).
        Uses multi-strategy approach with JS full-page scan and post-selection verification.
        """
        try:
            logger.info(f"Configuring Dola settings: Model={model}, Ratio={ratio}, Duration={duration}s", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

            # Dismiss any cookie popup that may have appeared again
            await self._dismiss_cookie_popup()

            await self.take_screenshot("before_settings")

            # ── Step 1: Click 'Create Video' button ──────────────────────────
            clicked = False
            for sel in ["button:has-text('Create Video')", "div[role='button']:has-text('Create Video')", "span:has-text('Create Video')", "a:has-text('Create Video')"]:
                try:
                    loc = self.page.locator(sel).first
                    if await loc.is_visible(timeout=1500):
                        await loc.click()
                        logger.info(f"Create Video clicked (CSS): {sel}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                        clicked = True
                        break
                except Exception:
                    continue

            if not clicked:
                js_click = await self._js_click_button_with_text("Create Video")
                if js_click:
                    logger.info(f"Create Video clicked (JS leaf node): '{js_click}'", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

            await self.page.wait_for_timeout(1000)
            await self.take_screenshot("after_create_video")

            # ── Step 2: Try to select 9:16 directly (buttons may already be visible) ──
            ratio_clicked = False
            for attempt in range(1, 5):
                logger.info(f"9:16 selection attempt {attempt}/4...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

                # Strategy A: JS full-page scan — most reliable
                js_result = await self.page.evaluate("""() => {
                    const targets = ['9:16', '9 : 16', '9/16'];
                    const tags = ['button', 'li', 'div', 'span', 'a', '[role="option"]', '[role="menuitem"]'];
                    for (const tag of tags) {
                        const els = document.querySelectorAll(tag);
                        for (const el of els) {
                            const t = (el.innerText || el.textContent || '').trim();
                            for (const target of targets) {
                                if (t === target || t.startsWith(target)) {
                                    const rect = el.getBoundingClientRect();
                                    if (rect.width > 0 && rect.height > 0) {
                                        el.click();
                                        return `JS_CLICK: ${tag} text="${t}"`;
                                    }
                                }
                            }
                        }
                    }
                    return null;
                }""")
                if js_result:
                    logger.info(f"9:16 selected via JS scan: {js_result}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                    ratio_clicked = True
                    break

                # Strategy B: Try opening a ratio dropdown first, then clicking 9:16
                dropdown_opened = False
                for sel in DolaSelectors.RATIO_DROPDOWN:
                    try:
                        loc = self.page.locator(sel).first
                        if await loc.is_visible(timeout=1000):
                            await loc.click()
                            logger.info(f"Ratio dropdown opened: {sel}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                            dropdown_opened = True
                            await self.page.wait_for_timeout(600)
                            break
                    except Exception:
                        continue

                if dropdown_opened:
                    await self.take_screenshot(f"after_ratio_dropdown_attempt{attempt}")
                    # Now try JS scan again after dropdown is open
                    js_result2 = await self.page.evaluate("""() => {
                        const targets = ['9:16', '9 : 16'];
                        const els = document.querySelectorAll('li, [role="option"], [role="menuitem"], div, button, span');
                        for (const el of els) {
                            const t = (el.innerText || el.textContent || '').trim();
                            for (const target of targets) {
                                if (t === target || t.startsWith(target)) {
                                    const rect = el.getBoundingClientRect();
                                    if (rect.width > 0 && rect.height > 0) {
                                        el.click();
                                        return `JS_AFTER_DROPDOWN: text="${t}"`;
                                    }
                                }
                            }
                        }
                        return null;
                    }""")
                    if js_result2:
                        logger.info(f"9:16 selected after dropdown: {js_result2}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                        ratio_clicked = True
                        break

                    # Strategy C: CSS selectors after dropdown open
                    for r_sel in DolaSelectors.RATIO_9_16:
                        try:
                            opt = self.page.locator(r_sel).first
                            if await opt.is_visible(timeout=1000):
                                await opt.click()
                                logger.info(f"9:16 selected (CSS): {r_sel}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                                ratio_clicked = True
                                break
                        except Exception:
                            continue
                    if ratio_clicked:
                        break

                await self.page.wait_for_timeout(800)
                # If not yet clicked, re-click Create Video and try again
                if not ratio_clicked and attempt < 4:
                    logger.info("Re-clicking Create Video before next ratio attempt...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                    await self._js_click_button_with_text("Create Video")
                    await self.page.wait_for_timeout(1000)

            # ── Step 3: Select Duration (15s or 10s) ─────────────────────────
            dur_str = f"{duration}s"
            duration_targets = [dur_str, f"{duration} s", f"{duration}sec", f"{duration} seconds", str(duration)]
            dur_clicked = await self.page.evaluate("""(targets) => {
                const tags = ['button', 'li', 'div', 'span', 'a', '[role="option"]', '[role="menuitem"]'];
                for (const tag of tags) {
                    const els = document.querySelectorAll(tag);
                    for (const el of els) {
                        const t = (el.innerText || el.textContent || '').trim().toLowerCase();
                        for (const target of targets) {
                            if (t === target.toLowerCase() || t.startsWith(target.toLowerCase())) {
                                const rect = el.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) {
                                    el.click();
                                    return `JS_DURATION_CLICK: ${tag} text="${t}"`;
                                }
                            }
                        }
                    }
                }
                return null;
            }""", duration_targets)
            if dur_clicked:
                logger.info(f"Duration {duration}s selected: {dur_clicked}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

            # ── Step 4: Post-selection screenshot & verification ──────────────
            await self.page.wait_for_timeout(800)
            await self.take_screenshot("after_ratio_select")

            if ratio_clicked:
                logger.info(f"✅ Create Video + 9:16 ratio + {duration}s duration configured successfully", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            else:
                # Log what buttons/text exist on page for debugging
                page_btns = await self.page.evaluate("""() => {
                    const btns = document.querySelectorAll('button, li, [role="option"]');
                    const texts = [];
                    for (const b of btns) {
                        const t = (b.innerText || '').trim();
                        if (t && t.length < 30) texts.push(t);
                    }
                    return [...new Set(texts)].slice(0, 40);
                }""")
                logger.warning(f"⚠️ Could not confirm 9:16 ratio selection! Visible buttons on page: {page_btns}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

            return True
        except Exception as e:
            logger.warning(f"Note during video settings configuration: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            return True

    async def switch_to_pro_mode(self) -> bool:
        """
        Switches composer mode from Fast to Pro using verified DOM selectors:
        1. Checks if Pro is already active.
        2. If Fast is active, clicks 'div[data-valid-btn="mode-select-action-btn"], button:has-text("Fast")'.
        3. Clicks the unique '[role="menuitem"]:has-text("Advanced Pro model"), text="Advanced Pro model"'.
        4. Waits for UI update and strictly verifies composer mode is 'Pro'.
        """
        try:
            logger.info("Checking composer mode (Fast -> Pro)...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            
            # Ensure composer mode buttons are rendered and visible
            try:
                await self.page.wait_for_selector('form button, [class*="composer"] button, [data-valid-btn="mode-select-action-btn"], button:has-text("Fast"), button:has-text("Pro")', timeout=10000)
            except Exception:
                pass
            await self.page.wait_for_timeout(1000)

            # Check if Pro is already active
            mode_before = await self.page.evaluate("""() => {
                const composer = document.querySelector('form, [class*="composer"], [class*="chat-input"], footer') || document.body;
                const btns = Array.from(composer.querySelectorAll('button, [role="button"], span, div'));
                for (const b of btns) {
                    const text = (b.innerText || b.textContent || '').trim();
                    if (text === 'Pro' || text.startsWith('Pro ')) return 'Pro';
                    if (text === 'Fast' || text.startsWith('Fast ')) return 'Fast';
                }
                return 'UNKNOWN';
            }""")

            logger.info(f"MODE BEFORE: {mode_before}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

            if mode_before == "Pro":
                logger.info("MODE AFTER: Pro", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                logger.info("✅ Pro mode verified", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return True

            # Open Mode dropdown
            fast_loc = self.page.locator('div[data-valid-btn="mode-select-action-btn"], button:has-text("Fast"), div[role="button"]:has-text("Fast")').first
            if await fast_loc.is_visible(timeout=2000):
                await fast_loc.click()
            else:
                await self.page.evaluate("""() => {
                    const composer = document.querySelector('form, [class*="composer"], [class*="chat-input"], footer') || document.body;
                    const btns = Array.from(composer.querySelectorAll('button, [role="button"], span, div'));
                    for (const b of btns) {
                        const text = (b.innerText || b.textContent || '').trim();
                        if (text === 'Fast' || text.startsWith('Fast ')) { b.click(); break; }
                    }
                }""")

            await self.page.wait_for_timeout(800)

            # Click actual Pro option using unique visible text 'Advanced Pro model'
            pro_option = self.page.locator("text='Advanced Pro model'").first
            if await pro_option.is_visible(timeout=2000):
                await pro_option.click()
            else:
                pro_option2 = self.page.locator("[role='menuitem']").filter(has_text="Advanced Pro model").first
                if await pro_option2.is_visible(timeout=1500):
                    await pro_option2.click()
                else:
                    logger.warning("Pro option locator not visible, clicking via JS...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                    await self.page.evaluate("""() => {
                        const items = Array.from(document.querySelectorAll('[role="menuitem"], div, span'));
                        for (const it of items) {
                            if ((it.innerText || '').includes('Advanced Pro model')) { it.click(); break; }
                        }
                    }""")

            await self.page.wait_for_timeout(1000)

            # Verify Pro mode in composer
            mode_after = await self.page.evaluate("""() => {
                const composer = document.querySelector('form, [class*="composer"], [class*="chat-input"], footer') || document.body;
                const btns = Array.from(composer.querySelectorAll('button, [role="button"], span, div'));
                for (const b of btns) {
                    const text = (b.innerText || b.textContent || '').trim();
                    if (text === 'Pro' || text.startsWith('Pro ')) return 'Pro';
                }
                return 'NOT_PRO';
            }""")

            if mode_after == "Pro":
                logger.info("MODE AFTER: Pro", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                logger.info("✅ Pro mode verified", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return True
            else:
                logger.error(f"❌ Pro selection failed. Mode is '{mode_after}'.", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                try:
                    fail_path = str(DATA_DIR / "logs" / "pro_selection_failed.png")
                    await self.page.screenshot(path=fail_path)
                    logger.info(f"Diagnostic screenshot saved to: {fail_path}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                except Exception:
                    pass

                logger.info("DEBUG: Pro selection failed — keeping browser open for 30s inspection.", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                await asyncio.sleep(30)
                return False

        except Exception as e:
            logger.error(f"Error switching to Pro mode: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            return False

    async def verify_generate_videos_skill_active(self) -> Tuple[bool, str]:
        """
        Inspects composer to verify whether 'Generate Videos' is active.
        Verified DOM: <SPAN class="react-renderer node-mention">...<SPAN class="label-OwNuNp">Generate Videos</SPAN></SPAN>
        """
        try:
            res = await self.page.evaluate("""() => {
                const composer = document.querySelector('form, [class*="composer"], [class*="chat-input"], footer') || document.body;
                
                // 1. Check verified ProseMirror node mention and labels
                const mentions = Array.from(composer.querySelectorAll('[class*="node-mention"], [class*="mention"], [class*="label-"], [class*="skill"], [class*="badge"], [class*="pill"]'));
                for (const m of mentions) {
                    const text = (m.innerText || m.textContent || '').trim();
                    if (text === 'Generate Videos' || text.toLowerCase() === 'generate videos') {
                        return { verified: true, active_skill: 'Generate Videos' };
                    }
                }

                // 2. Check full text of composer input
                const editor = composer.querySelector('.ProseMirror, textarea, [contenteditable="true"]');
                if (editor) {
                    const text = (editor.innerText || editor.textContent || '').trim();
                    if (text.includes('Generate Videos')) {
                        return { verified: true, active_skill: 'Generate Videos' };
                    }
                }

                // 3. Detect wrong attached skills
                const wrongSkills = ['homework', 'humanize writing', 'writing', 'translate', 'create image', 'generate docs', 'generate sheets'];
                for (const m of mentions) {
                    const text = (m.innerText || m.textContent || '').trim().toLowerCase();
                    for (const w of wrongSkills) {
                        if (text === w || text.startsWith(w)) {
                            return { verified: false, active_skill: text };
                        }
                    }
                }

                return { verified: false, active_skill: 'None' };
            }""")
            return bool(res.get("verified", False)), res.get("active_skill", "None")
        except Exception as e:
            logger.warning(f"Error inspecting composer active skill: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            return False, "Error"

    async def select_generate_videos_skill(self, max_retries: int = 3) -> bool:
        """
        Navigates Dola's New Chat interface:
        1. Clicks 'button:has-text("Skills")' in composer toolbar.
        2. Verifies that the Skills popup (div.popoverScroller-hVBaJp / div.panel-chKDv3) is open.
        3. Searches ONLY inside the Skills container for 'span.standardLabel-Qv_Pml:text-is("Generate Videos")'.
        4. Scrolls the container downward if not immediately visible.
        5. Clicks the exact 'Generate Videos' item.
        6. Strictly verifies composer active skill is 'Generate Videos'.
        """
        for attempt in range(1, max_retries + 1):
            logger.info(f"Selecting 'Generate Videos' skill (Attempt {attempt}/{max_retries})...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            await self._dismiss_cookie_popup()

            # Check if Generate Videos is ALREADY verified active on composer
            is_active, current_skill = await self.verify_generate_videos_skill_active()
            if is_active:
                logger.info("✅ Generate Videos skill verified active in composer.", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return True

            # Step 1: Click 'Skills' button in composer toolbar
            skills_btn = self.page.locator('button:has-text("Skills"), div[role="button"]:has-text("Skills"), [class*="skills"], button[title*="Skills"]').first
            btn_visible = False
            try:
                btn_visible = await skills_btn.is_visible(timeout=3000)
            except Exception:
                pass

            if btn_visible:
                await skills_btn.click()
                await self.page.wait_for_timeout(1000)
            else:
                # JS fallback click on any button containing "Skills"
                clicked_js = await self.page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('button, div[role="button"], span, div'));
                    for (const b of btns) {
                        const t = (b.innerText || b.textContent || '').trim();
                        if (t === 'Skills' || t.startsWith('Skills')) {
                            const rect = b.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                b.click();
                                return true;
                            }
                        }
                    }
                    return false;
                }""")
                if clicked_js:
                    await self.page.wait_for_timeout(1000)
                else:
                    logger.warning(f"Skills button not visible on Attempt {attempt}.", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                    await self.page.wait_for_timeout(1500)
                    continue

            # Step 2: Verify that the REAL Skills popup/container is open
            popup_locator = self.page.locator('div.popoverScroller-hVBaJp, div.panel-chKDv3, div[class*="popoverScroller"], div.list-aFsIpX').first
            popup_open = await popup_locator.is_visible(timeout=2500)

            if not popup_open:
                # Check fallback popup
                popup_open = await self.page.evaluate("""() => {
                    const el = document.querySelector('div[class*="popoverScroller"], div[class*="panel-"], div.list-aFsIpX');
                    return el && el.offsetWidth > 0 && el.offsetHeight > 0;
                }""")

            if not popup_open:
                logger.warning(f"Skills menu failed to open on Attempt {attempt}. Retrying...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                await self.page.wait_for_timeout(800)
                continue

            logger.info("Skills menu opened: PASS", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            logger.info("Skills container found: PASS", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

            # Step 3: Search ONLY inside the real Skills container & scroll if needed
            clicked_target = False
            for scroll_step in range(10):
                # Search for exact Generate Videos label
                gen_vid_label = self.page.locator("span:text-is('Generate Videos')").first
                if not await gen_vid_label.is_visible(timeout=500):
                    gen_vid_label = self.page.locator("span.standardLabel-Qv_Pml").filter(has_text="Generate Videos").first
                if not await gen_vid_label.is_visible(timeout=500):
                    gen_vid_label = self.page.locator("div.item-AHZ7rH:has-text('Generate Videos')").first

                if await gen_vid_label.is_visible(timeout=500):
                    await gen_vid_label.scroll_into_view_if_needed()
                    await gen_vid_label.click(force=True)
                    logger.info("Target skill item clicked: Generate Videos", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                    clicked_target = True
                    await self.page.wait_for_timeout(1500)
                    break
                else:
                    # Scroll container downward
                    await self.page.evaluate("""() => {
                        const container = document.querySelector('div[class*="popoverScroller"], div.list-aFsIpX, div.panel-chKDv3');
                        if (container) { container.scrollTop += 220; }
                    }""")
                    await self.page.wait_for_timeout(400)

            if not clicked_target:
                logger.warning(f"Generate Videos not found in Skills container on Attempt {attempt}.", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                await self.page.wait_for_timeout(800)
                continue

            # Step 4: STRICT VERIFICATION OF ACTIVE COMPOSER SKILL
            is_active, current_skill = await self.verify_generate_videos_skill_active()
            if is_active:
                logger.info("✅ Generate Videos skill verified active in composer.", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return True
            else:
                logger.warning(f"⚠️ Generate Videos composer verification failed (Attempt {attempt}/{max_retries}): Composer shows '{current_skill}'. Retrying...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                await self.page.wait_for_timeout(1000)

        # Complete Failure Handling
        logger.error("❌ Generate Videos skill could not be selected or verified after retries.", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
        return False

    async def handle_dynamic_dola_response(self, timeout_sec: float = 120.0) -> Tuple[str, str]:
        """
        Dynamically monitors Dola chat after prompt submission and handles whatever confirmation/action Dola requests.
        Returns (status, text):
        - "GENERATION_STARTED": Video generation started and confirmed.
        - "COMPLETED": Video ready ("Your video is ready.")
        - "TRUE_ERROR": Genuine unexpected generation failure.
        - "TIMEOUT": No response received within timeout.
        """
        import time as _t
        start_t = _t.time()
        confirmation_sent = False
        confirmation_sent_time = 0.0

        while _t.time() - start_t < timeout_sec:
            res_type, res_text = await self.classify_dola_response()

            if res_type == "QUOTA_LIMIT_EXCEEDED":
                logger.warning(f"Dola daily quota / limit detected: '{res_text}'", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return "QUOTA_LIMIT_EXCEEDED", res_text

            elif res_type == "UNEXPECTED_ERROR":
                logger.warning(f"Unexpected Dola error detected: '{res_text}'", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return "TRUE_ERROR", res_text

            elif res_type == "COMPLETED":
                logger.info(f"Video completion detected: '{res_text}'", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return "COMPLETED", res_text

            elif res_type == "VALID_GENERATION":
                logger.info(f"Generation start confirmed: '{res_text}'", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return "GENERATION_STARTED", res_text

            elif res_type in ("DURATION_CONFIRMATION_REQUIRED", "CONFIRMATION_REQUIRED"):
                if not confirmation_sent:
                    confirmation_sent = True
                    logger.info(f"Dola confirmation request detected: '{res_text}'. Waiting 7 seconds before confirming...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                    await self.page.wait_for_timeout(7000)
                    await self.submit_prompt("Confirmed, please start the video generation.")
                    await self.page.wait_for_timeout(3000)
                    start_t = _t.time()  # Reset timeout timer so Dola has fresh window to start generation
                    confirmation_sent_time = _t.time()

            # Check if Dola is asking any other confirmation questions (in English or Chinese)
            is_asking_confirmation = await self.page.evaluate("""() => {
                const text = (document.body.innerText || '').toLowerCase();
                const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                const confirmTriggers = [
                    'please confirm',
                    'once confirmed',
                    'inferred the optimal parameters',
                    'inferred parameters for your confirmation',
                    'do you want to continue',
                    'would you like to',
                    'shall i start',
                    'confirm to proceed',
                    'start the video generation',
                    'ready to generate',
                    '请确认',
                    '确认生成',
                    '是否继续',
                    '视频生成参数',
                    '已推断',
                    '确认后',
                    '开始生成视频'
                ];
                for (const l of lines) {
                    for (const trig of confirmTriggers) {
                        if (l.includes(trig)) return l;
                    }
                }
                return null;
            }""")

            if is_asking_confirmation and not confirmation_sent:
                confirmation_sent = True
                logger.info(f"Dynamic confirmation prompt detected: '{is_asking_confirmation}'. Waiting 7 seconds before confirming...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                await self.page.wait_for_timeout(7000)
                await self.submit_prompt("Confirmed, please start the video generation.")
                await self.page.wait_for_timeout(3000)
                start_t = _t.time()  # Reset timeout timer so Dola has fresh window to start generation
                confirmation_sent_time = _t.time()

            # If confirmation was sent and 10 seconds have elapsed without an error, generation is underway!
            if confirmation_sent and (_t.time() - confirmation_sent_time >= 10.0):
                logger.info("Confirmation successfully delivered to Dola. Proceeding to generation monitor.", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return "GENERATION_STARTED", "Confirmed and generation in progress"

            await self.page.wait_for_timeout(2000)

        # Fallback: If confirmation was sent and no error appeared, proceed to monitor
        if confirmation_sent:
            return "GENERATION_STARTED", "Confirmation sent, proceeding to monitor"

        return "TIMEOUT", "No valid generation confirmation received within timeout."

    async def capture_message_baseline(self) -> ChatMessageBaseline:
        """
        Captures a full page-text snapshot before prompt submission.
        This allows check_new_responses() to detect ONLY new text from Dola
        regardless of DOM structure / CSS class changes.
        """
        baseline = ChatMessageBaseline()
        try:
            # Full page text snapshot — primary detection method
            page_text = await self.page.evaluate("() => document.body.innerText || ''")
            baseline.page_text_snapshot = page_text

            # Also count download buttons / video elements for download detection
            v_count = 0
            for sel in DolaSelectors.DOWNLOAD_BUTTONS:
                v_count += await self.page.locator(sel).count()
            v_count += await self.page.locator("video").count()
            baseline.known_video_counts = v_count
            baseline.initial_message_count = v_count  # reuse for compat

        except Exception as e:
            logger.warning(f"Error establishing baseline: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

        logger.info(f"Baseline captured: page_text_len={len(baseline.page_text_snapshot)}, video_count={baseline.known_video_counts}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
        return baseline

    async def submit_prompt(self, prompt_text: str, max_retries: int = 3) -> bool:
        """
        Pastes the prompt into the composer after the active skill badge,
        automatically ensures '15 seconds Video Ratio 9:16' is appended at the end,
        strictly verifies that the composer text contains the prompt and active skill,
        and submits only upon successful verification.
        """
        suffix = "15 seconds Video Ratio 9:16"
        raw_text = (prompt_text or "").strip()
        if suffix.lower() not in raw_text.lower():
            orig_clean = f"{raw_text} {suffix}".strip()
        else:
            orig_clean = raw_text

        orig_len = len(orig_clean)
        norm_orig = " ".join(orig_clean.split())
        logger.info(f"Submitting prompt with locked suffix: '{orig_clean}'", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

        for attempt in range(1, max_retries + 1):
            try:
                await self.page.wait_for_timeout(500)

                # Focus composer editor at the end (after any attached mention badges)
                focused = await self.page.evaluate("""() => {
                    const ed = document.querySelector('.ProseMirror, [contenteditable="true"], textarea, input[type="text"]');
                    if (!ed) return false;
                    ed.focus();
                    if (ed.isContentEditable || ed.classList.contains('ProseMirror')) {
                        const range = document.createRange();
                        range.selectNodeContents(ed);
                        range.collapse(false); // Move to end after any mention nodes
                        const sel = window.getSelection();
                        sel.removeAllRanges();
                        sel.addRange(range);
                        return true;
                    }
                    return false;
                }""")

                if focused:
                    # Insert text via Playwright keyboard without wiping out DOM nodes
                    await self.page.keyboard.insert_text(" " + orig_clean)
                else:
                    # Fallback for standard textarea/input
                    target_input = self.page.locator("textarea, input[type='text']").first
                    if await target_input.is_visible(timeout=1000):
                        await target_input.fill(orig_clean)

                await self.page.wait_for_timeout(500)

                # Read back actual composer text
                composer_text = await self.page.evaluate("""() => {
                    const input = document.querySelector('.ProseMirror, [contenteditable="true"], textarea, input[type="text"]');
                    if (!input) return '';
                    return input.value || input.innerText || input.textContent || '';
                }""")
                
                comp_clean = composer_text.strip()
                comp_len = len(comp_clean)
                norm_comp = " ".join(comp_clean.split())

                logger.info(f"Original prompt length: {orig_len}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                logger.info(f"Composer prompt length: {comp_len}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

                # Verification check: Prompt content must be present in composer
                is_verified = (orig_clean in comp_clean) or (norm_orig in norm_comp) or (comp_len >= orig_len * 0.95 and norm_orig[:30] in norm_comp)

                if is_verified:
                    logger.info("✅ Prompt verification: PASS", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                else:
                    logger.warning(f"⚠️ Prompt verification: FAIL (Attempt {attempt}/{max_retries}) — composer text does not match original prompt", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                    await self.page.wait_for_timeout(800)
                    continue

                # Submit prompt via send button or Enter
                sent = False
                for sel in DolaSelectors.SEND_BUTTONS:
                    try:
                        btn = self.page.locator(sel).first
                        if await btn.is_visible(timeout=1500):
                            await btn.click(timeout=3000)
                            sent = True
                            break
                    except Exception:
                        continue

                if not sent:
                    await self.page.keyboard.press("Enter")

                await self.page.wait_for_timeout(1500)
                logger.info("Prompt submitted successfully.", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return True

            except Exception as e:
                logger.warning(f"Attempt {attempt} prompt submit error: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                await self.page.wait_for_timeout(1000)

        logger.error("❌ Prompt verification: FAIL — composer text does not match original prompt after retries.", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
        return False

    async def check_new_responses(self, baseline: ChatMessageBaseline) -> Tuple[str, str]:
        """
        Detects NEW Dola response messages after prompt submission.
        Compares current full page text against baseline snapshot.
        New text may be inserted ANYWHERE in the page (not just appended at end),
        so we check the ENTIRE current page for signals absent from the baseline.
        """
        try:
            current_text = await self.page.evaluate("() => document.body.innerText || ''")
            baseline_text = baseline.page_text_snapshot

            # Only proceed if page has grown (new content appeared)
            if len(current_text) <= len(baseline_text):
                return "NONE", ""

            # Log a sample of the new content for debugging
            new_sample = current_text[len(baseline_text):len(baseline_text)+150].strip()
            if new_sample:
                logger.info(f"New Dola text detected (+{len(current_text)-len(baseline_text)} chars): '{new_sample}'", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

            # 1. Check for Duration Warning — look in ENTIRE current text (not just new portion)
            #    because text may be inserted mid-page and slicing cuts sentences
            if self.pattern_engine.is_duration_warning(current_text) and not self.pattern_engine.is_duration_warning(baseline_text):
                logger.warning("Duration warning detected in new Dola response!", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return "WARNING", current_text

            # 2. Check for Generation Start — same approach: present now but absent at baseline
            is_start_now, has_primary_now, _ = self.pattern_engine.is_generation_start(current_text)
            is_start_before, _, _ = self.pattern_engine.is_generation_start(baseline_text)
            if is_start_now and not is_start_before:
                logger.info("Generation start confirmed in new Dola response!", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return "GENERATING", current_text

            return "NONE", ""

        except Exception as e:
            logger.warning(f"check_new_responses error: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            return "NONE", ""

    async def extract_and_update_credits(self, session_id: int) -> Optional[int]:
        """Scans Dola page text for remaining points phrase, updates database, and auto-expires session if < 3 credits remain in real-time."""
        try:
            import re
            from app.core.database import db
            page_text = await self.page.evaluate("() => document.body.innerText || ''")
            patterns = [
                r"(\d+)\s*(?:point|credit)s?\s*left",
                r"(?:have|left)\s+(\d+)\s*(?:point|credit)s?",
                r"you\s+have\s+(\d+)\s*(?:point|credit)",
            ]
            for p in patterns:
                m = re.search(p, page_text, re.IGNORECASE)
                if m:
                    remaining = int(m.group(1))
                    db.update_session_credits(session_id, remaining)
                    logger.info(f"Extracted & updated Dola credits for session ID {session_id}: {remaining} points left", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

                    # REAL-TIME AUTO-EXPIRE RULE: If remaining credits < 3, shift session to Expired in DB immediately!
                    if remaining < 3:
                        db.make_session_expired(session_id)
                        logger.warning(f"⚠️ Real-time Auto-Expire: Session ID {session_id} has {remaining} credits (< 3) — shifted to Expired status!", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                    return remaining
        except Exception as e:
            logger.warning(f"Failed to extract Dola credits: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
        return None

    async def trigger_extension_scroll_scan(self) -> None:
        """
        Executes smooth down & up page scrolling and 3-4 clicks on blank white background chat space
        to trigger extension MutationObserver & DOM events for video link detection & auto-download.
        """
        try:
            logger.debug("Executing scroll scan + 4x blank background clicks for extension video detection...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            await self.page.evaluate("""async () => {
                const totalHeight = document.body.scrollHeight || document.documentElement.scrollHeight || 2000;
                
                /* Helper to click blank background areas safely */
                const clickBlankBackground = (count) => {
                    const containers = document.querySelectorAll('main, div.chat-container, div.messages, body, div[role="main"]');
                    for (let i = 0; i < count; i++) {
                        for (const el of containers) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 100 && rect.height > 100) {
                                const evt = new MouseEvent('click', {
                                    clientX: rect.left + rect.width / 2 + (i * 12),
                                    clientY: rect.top + rect.height / 2 + (i * 12),
                                    bubbles: true,
                                    cancelable: true,
                                    view: window
                                });
                                el.dispatchEvent(evt);
                            }
                        }
                    }
                };

                /* 1. Scroll Down to bottom & click 2x blank white area */
                window.scrollTo({ top: totalHeight, behavior: 'smooth' });
                await new Promise(r => setTimeout(r, 400));
                clickBlankBackground(2);

                /* 2. Scroll Up to top & click 2x blank white area */
                window.scrollTo({ top: 0, behavior: 'smooth' });
                await new Promise(r => setTimeout(r, 400));
                clickBlankBackground(2);

                /* 3. Scroll to Middle & click 2x blank white area */
                window.scrollTo({ top: totalHeight / 2, behavior: 'smooth' });
                await new Promise(r => setTimeout(r, 400));
                clickBlankBackground(2);
            }""")
            await self.page.wait_for_timeout(800)
        except Exception as e:
            logger.warning(f"Scroll & click trigger failed (non-fatal): {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

    async def auto_confirm_warning(self, confirmation_text: str = "Yes, continue to generate the 10-second video.", model: str = "Seedance 2.0", ratio: str = "9:16", duration: int = 10) -> bool:
        """
        Handles Dola's duration / credit warning:
        1. Re-configures Create Video mode + 9:16 ratio + 10s duration
        2. Focuses chat input, types fixed confirmation message 'Yes, continue to generate the 10-second video.' and sends
        """
        fixed_text = "Yes, continue to generate the 10-second video."
        logger.info(f"Re-configuring Create Video + 9:16 ratio + {duration}s duration before sending confirmation...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

        # Step A: Re-configure Video Settings (Create Video + 9:16 ratio + 10s duration)
        await self.configure_video_settings(model=model, ratio=ratio, duration=duration)
        await self.page.wait_for_timeout(1000)

        # Step B: Type fixed confirmation in normal Dola chat input and send
        logger.info(f"Sending fixed confirmation: '{fixed_text}'", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
        return await self.submit_prompt(fixed_text)

    async def check_current_job_download_button(self, baseline: ChatMessageBaseline) -> bool:
        """
        Checks if a video element or download signal exists on Dola chat history.
        Detects: extension download buttons, Dola native video elements, native download links/buttons, completion text.
        """
        try:
            # 1. Check if any <video> or <source> element exists with valid src (http or blob)
            has_video_src = await self.page.evaluate("""() => {
                const videos = document.querySelectorAll('video');
                for (const v of videos) {
                    const src = v.currentSrc || v.src || '';
                    if (src.length > 5) return `video tag: ${src.substring(0, 50)}`;
                    const s = v.querySelector('source');
                    if (s && s.src && s.src.length > 5) return `source tag: ${s.src.substring(0, 50)}`;
                }
                return null;
            }""")
            if has_video_src:
                logger.info(f"Active video element detected on page: {has_video_src}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return True

            # 2. Check extension download buttons (.purza-dl-btn) or native Download buttons
            has_dl_btn = await self.page.evaluate("""() => {
                const btns = document.querySelectorAll('.purza-dl-btn, a[download], button[aria-label*="Download"]');
                for (const b of btns) {
                    const rect = b.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) return true;
                }
                return false;
            }""")
            if has_dl_btn:
                logger.info("Download button element detected on page!", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return True

            # 3. Check ENTIRE page text for completion phrases
            completion_phrases = [
                "your video is ready",
                "video is ready",
                "generation complete",
                "has been generated",
                "download your video",
                "ready to download",
            ]
            page_text = (await self.page.evaluate("() => document.body.innerText || ''")).lower()
            for phrase in completion_phrases:
                if phrase in page_text:
                    logger.info(f"Dola completion phrase detected in page text: '{phrase}'", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                    return True

        except Exception as e:
            logger.warning(f"check_current_job_download_button error: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

        return False

    async def click_download_button(self) -> bool:
        """
        Clicks the extension's .purza-dl-btn or Dola's native video download button.
        Explicitly excludes top header buttons like 'Download for Windows'.
        """
        try:
            clicked_info = await self.page.evaluate("""() => {
                // 1. Extension download button
                const purzaBtn = document.querySelector('.purza-dl-btn');
                if (purzaBtn) {
                    purzaBtn.click();
                    return "Extension purza-dl-btn clicked";
                }

                // 2. Scan all buttons / links, EXCLUDING 'Download for Windows'
                const all = document.querySelectorAll('button, a, div[role="button"], [aria-label*="download"]');
                for (const el of all) {
                    const text = (el.innerText || el.textContent || '').trim();
                    const aria = (el.getAttribute('aria-label') || '').trim();
                    const title = (el.getAttribute('title') || '').trim();
                    const combined = `${text} ${aria} ${title}`.toLowerCase();

                    // Skip header installer buttons!
                    if (combined.includes('windows') || combined.includes('installer') || combined.includes('desktop app')) {
                        continue;
                    }

                    if (combined.includes('download') || el.hasAttribute('download')) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            el.click();
                            return `Video download element clicked: "${text || aria || title}"`;
                        }
                    }
                }
                return null;
            }""")

            if clicked_info:
                logger.info(f"click_download_button: {clicked_info}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return True
            else:
                logger.debug("No video download button found (ignored header installer button)", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
        except Exception as e:
            logger.warning(f"click_download_button error: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
        return False

    async def get_download_url_from_button(self) -> Optional[str]:
        """
        Extracts the video download URL from the extension's .purza-dl-btn button.
        The extension stores the URL in data-url, data-src, href, or similar attributes.
        Call this IMMEDIATELY when download button is detected (before any reload).
        """
        try:
            result = await self.page.evaluate("""() => {
                // Check purza extension download button
                const btn = document.querySelector('.purza-dl-btn');
                if (btn) {
                    // Try all common data attributes
                    const url = btn.dataset.url || btn.dataset.src || btn.dataset.href
                              || btn.getAttribute('data-url') || btn.getAttribute('data-src')
                              || btn.getAttribute('href') || '';
                    if (url && url.startsWith('http')) return url;
                    // Also check onclick attribute for URL
                    const onclick = btn.getAttribute('onclick') || '';
                    const match = onclick.match(/https?:\\/\\/[^'"\\s]+/);
                    if (match) return match[0];
                }
                // Also check any <a download> links
                const dlLink = document.querySelector('a[download][href*="http"]');
                if (dlLink) return dlLink.href;
                // Also check button onclick for download URLs
                const allBtns = document.querySelectorAll('button[onclick*="http"]');
                for (const b of allBtns) {
                    const m = (b.getAttribute('onclick')||'').match(/https?:\\/\\/[^'"\\s]+/);
                    if (m) return m[0];
                }
                return null;
            }""")
            if result:
                logger.info(f"Got URL from download button: {result[:80]}...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return result

            # Also scan all anchor tags for mp4 links
            mp4_result = await self.page.evaluate("""() => {
                for (const a of document.querySelectorAll('a')) {
                    if (a.href && (a.href.includes('.mp4') || a.href.includes('video'))) return a.href;
                }
                return null;
            }""")
            if mp4_result:
                logger.info(f"Found MP4 link in anchor: {mp4_result[:80]}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return mp4_result

            logger.info("No URL found in download buttons or anchors.", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
        except Exception as e:
            logger.warning(f"get_download_url_from_button error: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
        return None

    async def get_video_src_from_page(self) -> Optional[str]:
        """
        Extracts the video source URL directly from the DOM.
        Uses JavaScript evaluation to find ALL possible video URLs on the page.
        """
        try:
            # Small wait to let DOM settle after video appears
            await self.page.wait_for_timeout(1000)

            # JS scan: find all video src, currentSrc, and source children
            js_result = await self.page.evaluate("""() => {
                const urls = [];
                
                // 1. All <video> elements
                document.querySelectorAll('video').forEach(v => {
                    if (v.currentSrc && v.currentSrc.startsWith('http')) urls.push(v.currentSrc);
                    if (v.src && v.src.startsWith('http')) urls.push(v.src);
                });
                
                // 2. All <source> elements inside <video>
                document.querySelectorAll('video source').forEach(s => {
                    if (s.src && s.src.startsWith('http')) urls.push(s.src);
                });
                
                // 3. Any <a> download links with .mp4
                document.querySelectorAll('a[href*=".mp4"], a[download]').forEach(a => {
                    if (a.href && a.href.startsWith('http')) urls.push(a.href);
                });
                
                // 4. Check purza download button data (if extension injected it)
                document.querySelectorAll('.purza-dl-btn').forEach(btn => {
                    if (btn.dataset && btn.dataset.url) urls.push(btn.dataset.url);
                });
                
                // Deduplicate and return
                return [...new Set(urls)].filter(u => u && u.startsWith('http'));
            }""")

            if js_result and len(js_result) > 0:
                url = js_result[0]
                logger.info(f"Found {len(js_result)} video URL(s). Using: {url[:80]}...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return url

            # Fallback: count and log what's on the page for diagnosis
            v_count = await self.page.locator("video").count()
            logger.info(f"No video URLs found via JS scan. <video> elements on page: {v_count}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

            # Final fallback: check by Playwright locator with attribute scan
            for i in range(v_count):
                try:
                    v = self.page.locator("video").nth(i)
                    src = await v.get_attribute("src", timeout=3000)
                    if src and src.startswith("http"):
                        return src
                    current_src = await self.page.evaluate("(el) => el.currentSrc || ''", await v.element_handle())
                    if current_src and current_src.startswith("http"):
                        return current_src
                except Exception:
                    continue

        except Exception as e:
            logger.warning(f"get_video_src_from_page error: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
        return None

    async def diagnose_video_page(self) -> Dict[str, Any]:
        """
        Executes an exhaustive DOM & Network resource inspection immediately after 'Your video is ready.'
        Strictly filters out non-video assets (.js, .css, images, header installer buttons).
        Logs exact counts, valid video sources, shadow DOM elements, iframes, and valid download buttons.
        """
        try:
            diag = await self.page.evaluate("""() => {
                const isValidMediaUrl = (url) => {
                    if (!url || typeof url !== 'string' || url.length < 5) return false;
                    const lower = url.toLowerCase();
                    // Simplified validation: accept blob URLs or any URL containing common video extensions or typical video path segments
                    return lower.startsWith('blob:') || lower.includes('.mp4') || lower.includes('.webm') || lower.includes('.mov') || lower.includes('video_mp4') || lower.includes('/video/') || lower.includes('/media/') || lower.includes('/videos/');
                };

                const info = {
                    video_count: 0,
                    valid_video_sources: [],
                    valid_source_tags: [],
                    a_download_count: 0,
                    valid_download_buttons: [],
                    aria_download_count: 0,
                    iframe_count: document.querySelectorAll('iframe').length,
                    shadow_video_count: 0,
                    performance_media_urls: []
                };

                // 1. Scan Main DOM Videos
                document.querySelectorAll('video').forEach(v => {
                    info.video_count++;
                    const s1 = v.currentSrc || v.src || '';
                    if (isValidMediaUrl(s1)) info.valid_video_sources.push(`src: ${s1}`);
                    v.querySelectorAll('source').forEach(s => {
                        if (isValidMediaUrl(s.src)) info.valid_source_tags.push(s.src);
                    });
                });

                // 2. Scan Shadow DOM Roots recursively
                const scanShadow = (root) => {
                    if (!root) return;
                    root.querySelectorAll('video').forEach(v => {
                        info.shadow_video_count++;
                        const s1 = v.currentSrc || v.src || '';
                        if (isValidMediaUrl(s1)) info.valid_video_sources.push(`shadow src: ${s1}`);
                    });
                    root.querySelectorAll('*').forEach(el => {
                        if (el.shadowRoot) scanShadow(el.shadowRoot);
                    });
                };
                scanShadow(document);

                // 3. Anchors & Buttons (Exclude header installer buttons)
                document.querySelectorAll('a[download]').forEach(a => {
                    const href = a.href || '';
                    if (isValidMediaUrl(href)) info.a_download_count++;
                });

                document.querySelectorAll('button, a, div[role="button"]').forEach(b => {
                    const text = (b.innerText || b.textContent || '').trim().toLowerCase();
                    const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                    const title = (b.getAttribute('title') || '').toLowerCase();
                    const combined = `${text} ${aria} ${title}`;

                    // Skip header installer buttons!
                    if (combined.includes('windows') || combined.includes('installer') || combined.includes('desktop app')) {
                        return;
                    }

                    if (combined.includes('download')) {
                        const rect = b.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            info.valid_download_buttons.push(text.substring(0, 30) || aria.substring(0, 30) || 'download_button');
                        }
                    }
                });

                // 4. Performance Resource Entries (Strict MP4/blob filter)
                try {
                    const resources = performance.getEntriesByType('resource');
                    for (const r of resources) {
                        if (r.name && isValidMediaUrl(r.name)) {
                            info.performance_media_urls.push(r.name.substring(0, 80));
                        }
                    }
                } catch (e) {}

                return info;
            }""")

            logger.info("================ LIVE VIDEO DIAGNOSTICS ================", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            logger.info(f"📊 Videos in Main DOM: {diag.get('video_count', 0)} | In Shadow DOM: {diag.get('shadow_video_count', 0)}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            logger.info(f"📊 Valid Video Sources Found: {diag.get('valid_video_sources', [])}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            logger.info(f"📊 Valid <source> Tags Found: {diag.get('valid_source_tags', [])}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            logger.info(f"📊 Valid <a download> count: {diag.get('a_download_count', 0)}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            logger.info(f"📊 Valid download buttons found: {diag.get('valid_download_buttons', [])}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            logger.info(f"📊 Iframes count: {diag.get('iframe_count', 0)}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            logger.info(f"📊 Valid performance media URLs: {diag.get('performance_media_urls', [])}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            logger.info("========================================================", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

            return diag
        except Exception as e:
            logger.warning(f"diagnose_video_page error: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            return {}

    async def wait_for_video_element_or_source(self, timeout_sec: float = 30.0) -> bool:
        """
        Polls DOM every 1s after 'Your video is ready.' until a genuine video element, usable media source,
        or valid native download button lands on the page.
        """
        logger.info("Waiting for actual video element/source...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
        start_t = time.time()
        poll_count = 0
        
        while time.time() - start_t < timeout_sec:
            poll_count += 1
            diag = await self.diagnose_video_page()

            # A. Check for valid video sources
            valid_sources = diag.get("valid_video_sources") or diag.get("valid_source_tags") or diag.get("performance_media_urls")
            if valid_sources:
                logger.info(f"✅ VALID VIDEO SOURCE FOUND: {valid_sources[0]}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return True

            # B. Check for valid native download buttons (excluding Windows installer)
            if diag.get("valid_download_buttons") or diag.get("a_download_count", 0) > 0:
                logger.info("✅ VALID NATIVE DOWNLOAD BUTTON FOUND!", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return True

            # C. Check if video tag exists with non-empty src
            if diag.get("video_count", 0) > 0 or diag.get("shadow_video_count", 0) > 0:
                if diag.get("valid_video_sources"):
                    logger.info("✅ VALID VIDEO ELEMENT WITH SOURCE FOUND!", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                    return True

            logger.info(f"No valid video source yet — continuing poll... ({poll_count}/{int(timeout_sec)}s)", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            await self.page.wait_for_timeout(1000)

        logger.warning(f"❌ No valid video source or native download control appeared within {int(timeout_sec)}s timeout.", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
        return False

    async def classify_dola_response(self) -> Tuple[str, str]:
        """
        Broad EXPECTED vs UNEXPECTED Dola response classifier.
        Evaluates messages bottom-up (reverse chronological order) so the most recent
        state of the conversation takes immediate precedence.
        """
        try:
            res = await self.page.evaluate("""() => {
                const text = document.body.innerText || '';
                const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                
                const normalize = (str) => {
                    return str
                        .toLowerCase()
                        .replace(/['’`]/g, "'")
                        .replace(/["”]/g, '"')
                        .replace(/\\s+/g, ' ')
                        .trim();
                };

                const quotaPhrases = [
                    "currently generating video longer",
                    "longer than 10 second",
                    "longer then 10 second",
                    "longer than 10s",
                    "longer then 10s",
                    "10 seconds is not supported",
                    "10 second is not supported",
                    "generating video longer",
                    "daily limit",
                    "quota exceeded",
                    "暂不支持超过10秒",
                    "不支持超过10秒",
                    "超过10秒",
                    "每日额度已满",
                    "点数不足"
                ];

                const completionPhrases = [
                    "your video is ready",
                    "video is ready",
                    "generation complete",
                    "has been generated"
                ];

                const validStartPhrases = [
                    "generating your",
                    "generating video",
                    "generating your video",
                    "start video generation",
                    "video is generating",
                    "will be generated using",
                    "video will be generated",
                    "points left today",
                    "ready in",
                    "正在生成视频",
                    "开始生成视频",
                    "视频生成中"
                ];

                const durationPhrases = [
                    "please confirm",
                    "once confirmed",
                    "inferred the optimal parameters",
                    "inferred parameters for your confirmation",
                    "video generation parameters",
                    "start the video generation",
                    "do you want to continue generating",
                    "continue generating for you",
                    "continue generating",
                    "continue generating the 10-second video",
                    "continue generating for",
                    "请确认",
                    "确认生成",
                    "是否继续生成",
                    "是否继续",
                    "视频生成参数",
                    "已推断",
                    "确认后将开始",
                    "开始生成视频",
                    "生成视频参数",
                    "确认参数"
                ];

                const errorPhrases = [
                    "something went wrong",
                    "unable to process",
                    "try again",
                    "generation failed",
                    "internal error",
                    "server error",
                    "cannot generate",
                    "can't generate",
                    "cant generate",
                    "we can't generate",
                    "we cant generate",
                    "we cannot generate",
                    "unable to generate",
                    "unsupported type",
                    "unsupported element",
                    "failed to generate",
                    "content cannot be generated",
                    "type of element",
                    "error occurred",
                    "an error occurred",
                    "could not generate",
                    "couldn't generate",
                    "couldnt generate"
                ];

                // Evaluate lines bottom-up (most recent messages first)
                for (let i = lines.length - 1; i >= 0; i--) {
                    const norm = normalize(lines[i]);

                    // 1. Quota / Daily Limit Exhaustion signal (First Priority)
                    for (const phrase of quotaPhrases) {
                        if (norm.includes(phrase)) {
                            return { type: "QUOTA_LIMIT_EXCEEDED", text: lines[i] };
                        }
                    }

                    // 2. Completion signal
                    for (const phrase of completionPhrases) {
                        if (norm.includes(phrase)) {
                            return { type: "COMPLETED", text: lines[i] };
                        }
                    }

                    // 3. Active generation start / ongoing signal
                    for (const phrase of validStartPhrases) {
                        if (norm.includes(phrase)) {
                            return { type: "VALID_GENERATION", text: lines[i] };
                        }
                    }

                    // 4. Confirmation required signal (English & Chinese)
                    for (const phrase of durationPhrases) {
                        if (norm.includes(phrase)) {
                            return { type: "DURATION_CONFIRMATION_REQUIRED", text: lines[i] };
                        }
                    }

                    // 5. Error signal
                    for (const phrase of errorPhrases) {
                        if (norm.includes(phrase)) {
                            return { type: "UNEXPECTED_ERROR", text: lines[i] };
                        }
                    }
                }

                return { type: "UNKNOWN", text: "" };
            }""")
            if res and isinstance(res, dict):
                return res.get("type", "UNKNOWN"), res.get("text", "")
        except Exception:
            pass
        return "UNKNOWN", ""

    async def check_error_response(self) -> Tuple[bool, str]:
        """
        Scans Dola chat text for any TRUE UNEXPECTED generation error response.
        Returns (has_error, error_text). Will NOT flag duration warning responses as errors.
        """
        ctype, text = await self.classify_dola_response()
        if ctype == "UNEXPECTED_ERROR":
            return True, text
        return False, ""

    async def check_completion_response(self) -> Tuple[bool, str]:
        """
        Scans Dola chat text for exact completion response ('Your video is ready.', 'generation complete', etc.).
        Returns (is_ready, response_line).
        """
        try:
            line = await self.page.evaluate("""() => {
                const text = document.body.innerText || '';
                const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                for (const l of lines) {
                    const lower = l.toLowerCase();
                    if (lower.includes('your video is ready') || lower.includes('video is ready') || lower.includes('generation complete')) {
                        return l;
                    }
                }
                // Also check if video tag or purza button is rendered on DOM
                if (document.querySelector('video') || document.querySelector('.purza-dl-btn')) {
                    return "Your video is ready.";
                }
                return null;
            }""")
            if line:
                return True, line
        except Exception:
            pass
        return False, ""

    async def fetch_and_save_video(self, output_folder: str) -> Optional[str]:
        """
        Robustly extracts video source (HTTP URL, Blob Base64, or Performance Network Resource) from Dola DOM and saves directly to disk.
        Returns the absolute filepath of the saved .mp4 file or None.
        """
        try:
            import base64
            import urllib.request

            # Step 0: Ensure Purza download button or native download buttons are clicked to activate video stream
            try:
                await self.click_download_button()
            except Exception:
                pass

            # Step 1: Scan DOM + Performance Resource Timing for all video sources (http or blob)
            sources = await self.page.evaluate("""() => {
                const isValidMediaUrl = (url) => {
                    if (!url || typeof url !== 'string' || url.length < 5) return false;
                    const lower = url.toLowerCase();
                    // Simplified validation: accept blob URLs or any URL containing common video extensions or typical video path segments
                    return lower.startsWith('blob:') || lower.includes('.mp4') || lower.includes('.webm') || lower.includes('.mov') || lower.includes('video_mp4') || lower.includes('/video/') || lower.includes('/media/') || lower.includes('/videos/');
                };

                const urls = [];
                
                // 1. All <video> and <source> elements
                document.querySelectorAll('video').forEach(v => {
                    if (v.currentSrc && isValidMediaUrl(v.currentSrc)) urls.push(v.currentSrc);
                    if (v.src && isValidMediaUrl(v.src)) urls.push(v.src);
                    v.querySelectorAll('source').forEach(s => {
                        if (s.src && isValidMediaUrl(s.src)) urls.push(s.src);
                    });
                });

                // 2. All Purza download buttons (.purza-dl-btn)
                document.querySelectorAll('.purza-dl-btn').forEach(btn => {
                    const u = btn.dataset.url || btn.dataset.src || btn.getAttribute('data-url') || btn.getAttribute('data-src') || btn.getAttribute('href') || '';
                    if (isValidMediaUrl(u)) urls.push(u);
                });

                // 3. All anchor download links or mp4 links
                document.querySelectorAll('a[download], a[href*=".mp4"], a[href*="video"]').forEach(a => {
                    if (a.href && isValidMediaUrl(a.href)) urls.push(a.href);
                });

                // 4. Performance resource timing entries (Strict MP4/blob filter)
                try {
                    const resources = performance.getEntriesByType('resource');
                    for (const r of resources) {
                        if (r.name && isValidMediaUrl(r.name)) {
                            urls.push(r.name);
                        }
                    }
                } catch (e) {}

                return [...new Set(urls)].filter(u => u && typeof u === 'string' && u.length > 5);
            }""")

            if not sources:
                logger.debug("fetch_and_save_video: No video sources found in DOM/Network scan.", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                return None

            os.makedirs(output_folder, exist_ok=True)

            for target_url in sources:
                filename = f"Dola_Video_{int(time.time())}.mp4"
                dest_path = str(Path(output_folder) / filename)

                # Option A: Standard HTTP / HTTPS MP4 link
                if target_url.startswith("http"):
                    try:
                        logger.info(f"📥 Downloading HTTP video stream directly: {target_url[:70]}...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                        urllib.request.urlretrieve(target_url, dest_path)
                        if Path(dest_path).exists() and Path(dest_path).stat().st_size > 10000:
                            logger.info(f"🎉 Direct HTTP video saved: {filename} ({Path(dest_path).stat().st_size/1024/1024:.2f} MB)", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                            return dest_path
                    except Exception as e:
                        logger.warning(f"HTTP video retrieval failed: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

                # Option B: Blob URL — fetch ArrayBuffer Base64 via Playwright JavaScript
                elif target_url.startswith("blob:"):
                    try:
                        logger.info("📥 Extracting Blob video data from Chromium main world...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                        b64_data = await self.page.evaluate("""async (blobUrl) => {
                            try {
                                const resp = await fetch(blobUrl);
                                const blob = await resp.blob();
                                return new Promise((resolve) => {
                                    const reader = new FileReader();
                                    reader.onloadend = () => {
                                        const res = reader.result || '';
                                        const parts = res.split(',');
                                        resolve(parts.length > 1 ? parts[1] : null);
                                    };
                                    reader.onerror = () => resolve(null);
                                    reader.readAsDataURL(blob);
                                });
                            } catch (e) {
                                return null;
                            }
                        }""", target_url)

                        if b64_data:
                            raw_bytes = base64.b64decode(b64_data)
                            if len(raw_bytes) > 10000:
                                with open(dest_path, "wb") as f:
                                    f.write(raw_bytes)
                                logger.info(f"🎉 Blob video converted & saved to disk: {filename} ({len(raw_bytes)/1024/1024:.2f} MB)", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                                return dest_path
                    except Exception as e:
                        logger.warning(f"Blob base64 conversion failed: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

        except Exception as e:
            logger.warning(f"fetch_and_save_video error: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

    async def initialize_lazy_video_block(self) -> bool:
        """
        Checks for Dola's lazy-loaded video container blocks (.block-video-*, .play-icon-wrapper-*, .video-player-wrapper-*)
        and clicks to force Dola frontend to mount the actual <video> tag into the DOM.
        (Ported directly from E:\\Dola Automation)
        """
        try:
            selectors = [
                ".block-video-MzfWVN",
                ".play-icon-wrapper-wkMy04",
                ".video-player-wrapper-IZ7Zoq",
                "video",
                "[class*='block-video']",
                "[class*='play-icon']",
                "[class*='video-player']"
            ]
            for sel in selectors:
                try:
                    count = await self.page.locator(sel).count()
                    if count > 0:
                        loc = self.page.locator(sel).last
                        logger.info(f"🎥 Lazy-loaded video block detected ({sel}, total: {count}). Clicking to initialize video...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                        await loc.click(timeout=5000, force=True)
                        await asyncio.sleep(2.0)  # Allow DOM time to mount <video> tag
                        return True
                except Exception:
                    continue
            return False
        except Exception as e:
            logger.debug(f"initialize_lazy_video_block notice: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            return False

    async def trigger_smart_download_extraction(self, output_folder: Optional[str] = None) -> bool:
        """
        Triggers Blob/HTTP smart download by injecting a temporary anchor element and calling a.click().
        Fires Playwright page.on("download") natively.
        (Reconciled directly from E:\\Dola Automation)
        """
        if getattr(self, "job_completed", False):
            return False
        try:
            res = await self.page.evaluate("""async () => {
                let v = document.querySelector('video');
                if (!v) {
                    const videoBlocks = document.querySelectorAll('.block-video-MzfWVN, .play-icon-wrapper-wkMy04, .video-player-wrapper-IZ7Zoq, [class*="video-player"], [class*="block-video"], [class*="play-icon"]');
                    if (videoBlocks.length > 0) {
                        videoBlocks[videoBlocks.length - 1].click();
                        await new Promise(r => setTimeout(r, 1500));
                        v = document.querySelector('video');
                    }
                }

                if (v) {
                    const url = v.currentSrc || v.src || (v.querySelector('source') ? v.querySelector('source').src : '');
                    if (url) {
                        if (url.startsWith('blob:')) {
                            try {
                                const response = await fetch(url);
                                const blob = await response.blob();
                                const a = document.createElement('a');
                                a.href = URL.createObjectURL(blob);
                                a.download = 'generated_video.mp4';
                                document.body.appendChild(a);
                                a.click();
                                document.body.removeChild(a);
                                return 'blob_triggered';
                            } catch (err) {
                                return 'blob_fetch_failed';
                            }
                        }

                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'generated_video.mp4';
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        return 'url_triggered';
                    }
                }

                // Check for video download button or direct video link
                const dlBtns = Array.from(document.querySelectorAll('button, a'));
                for (const el of dlBtns) {
                    const txt = (el.innerText || el.getAttribute('title') || el.getAttribute('aria-label') || '').toLowerCase();
                    if ((txt.includes('download') || el.hasAttribute('download')) && !txt.includes('windows') && !txt.includes('desktop')) {
                        el.click();
                        return 'btn_clicked';
                    }
                }

                return 'no_video';
            }""")
            logger.info(f"Smart Download Extraction Result: {res}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            return res in ['blob_triggered', 'url_triggered', 'btn_clicked']
        except Exception as e:
            logger.warning(f"trigger_smart_download_extraction notice: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            return False

    async def fast_download_via_context_request(self, output_folder: str) -> Optional[str]:
        """
        Fetches the video URL directly using Playwright browser_context.request.get(video_url),
        direct fetch/blob decoding, or anchor download, and writes bytes directly to disk.
        """
        if getattr(self, "job_completed", False):
            return None
        try:
            video_urls = await self.page.evaluate("""() => {
                const urls = [];
                // 1. Check all video tags
                document.querySelectorAll('video').forEach(v => {
                    if (v.currentSrc) urls.push(v.currentSrc);
                    if (v.src) urls.push(v.src);
                });
                // 2. Check source tags
                document.querySelectorAll('video source').forEach(s => {
                    if (s.src) urls.push(s.src);
                });
                // 3. Check <a> links with mp4/video/download
                document.querySelectorAll('a[download], a[href*=".mp4"], a[href*="video"]').forEach(a => {
                    if (a.href) urls.push(a.href);
                });
                return [...new Set(urls)].filter(u => u && (u.startsWith('http') || u.startsWith('blob:')));
            }""")
            
            if not video_urls:
                return None

            for video_url in video_urls:
                if video_url in self.processed_urls:
                    continue
                self.processed_urls.add(video_url)

                logger.info(f"Found video media source: {video_url[:80]}...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

                # Case A: Standard HTTP(S) URL
                if video_url.startswith("http"):
                    try:
                        logger.info("Initiating direct download via browser_context.request.get...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                        response = await self.page.context.request.get(video_url)
                        if response.ok:
                            video_bytes = await response.body()
                            if len(video_bytes) > 50000:
                                os.makedirs(output_folder, exist_ok=True)
                                filename = f"Dola_Direct_{int(time.time()*1000)}.mp4"
                                filepath = str(Path(output_folder) / filename)
                                with open(filepath, "wb") as f:
                                    f.write(video_bytes)
                                logger.info(f"🎉 SUCCESS! Downloaded via browser_context.request.get: {filename} ({len(video_bytes)/1024/1024:.2f} MB)", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                                return filepath
                    except Exception as http_err:
                        logger.warning(f"HTTP context download attempt notice: {http_err}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

                # Case B: Blob URL extraction via in-page fetch + Base64 conversion
                elif video_url.startswith("blob:"):
                    try:
                        logger.info("Extracting blob video stream via in-page Base64 reader...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                        b64_data = await self.page.evaluate("""async (blobUrl) => {
                            try {
                                const res = await fetch(blobUrl);
                                const blob = await res.blob();
                                return new Promise((resolve, reject) => {
                                    const reader = new FileReader();
                                    reader.onloadend = () => {
                                        const resStr = reader.result || '';
                                        const b64 = resStr.includes(',') ? resStr.split(',')[1] : resStr;
                                        resolve(b64);
                                    };
                                    reader.onerror = reject;
                                    reader.readAsDataURL(blob);
                                });
                            } catch(e) {
                                return null;
                            }
                        }""", video_url)

                        if b64_data and len(b64_data) > 50000:
                            import base64
                            video_bytes = base64.b64decode(b64_data)
                            if len(video_bytes) > 50000:
                                os.makedirs(output_folder, exist_ok=True)
                                filename = f"Dola_Blob_{int(time.time()*1000)}.mp4"
                                filepath = str(Path(output_folder) / filename)
                                with open(filepath, "wb") as f:
                                    f.write(video_bytes)
                                logger.info(f"🎉 SUCCESS! Downloaded & decoded blob video: {filename} ({len(video_bytes)/1024/1024:.2f} MB)", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
                                return filepath
                    except Exception as blob_err:
                        logger.warning(f"Blob extraction notice: {blob_err}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

        except Exception as e:
            logger.warning(f"fast_download_via_context_request notice: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
        return None

    async def reload_page(self) -> bool:
        """Executes page reload cleanly to trigger extension auto-download."""
        try:
            logger.info("Reloading Dola page (page.reload())...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            # Give pending JS/async evaluate tasks 500ms to complete cleanly before page navigation
            await self.page.wait_for_timeout(500)
            await self.page.reload(timeout=30000, wait_until="domcontentloaded")
            await self.page.wait_for_timeout(2000)
            return True
        except Exception as e:
            logger.error(f"Error reloading page: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            return False

    async def interact_with_video_card(self) -> bool:
        """
        Executes Playwright browser-level post-generation video interaction:
        1. Locates the message/container with 'Your video is ready.'
        2. Identifies the closest relevant generated video/media/card container.
        3. Scrolls the container into view using Playwright (locator.scroll_into_view_if_needed()).
        4. Uses Playwright locator.hover() on the media/card element.
        5. Waits ~1 second.
        6. Uses Playwright locator.click() on the media/card element.
        All actions run completely isolated within this browser context, without touching the physical OS mouse.
        """
        try:
            logger.info("🎬 Executing Playwright post-generation video card interaction...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

            # Step 1: Locate message container containing "Your video is ready."
            ready_loc = self.page.locator("text=/your video is ready/i").last
            card_locator = None

            if await ready_loc.count() > 0:
                try:
                    # Find parent/ancestor message or card container
                    parent_loc = ready_loc.locator("xpath=./ancestor::div[contains(@class, 'message') or contains(@class, 'card') or contains(@class, 'container') or position()<=5]").last
                    if await parent_loc.count() > 0:
                        card_locator = parent_loc
                    else:
                        card_locator = ready_loc
                except Exception:
                    card_locator = ready_loc

            # Fallback locator if ready text locator is not found
            if not card_locator or await card_locator.count() == 0:
                for sel in [".purza-dl-btn", "video", "canvas", "[data-video-url]", "div[class*='video']", "div[class*='card']"]:
                    loc = self.page.locator(sel).last
                    if await loc.count() > 0:
                        card_locator = loc
                        break

            if not card_locator or await card_locator.count() == 0:
                card_locator = self.page.locator("body")

            # Step 3: Scroll container into view using Playwright
            logger.info("1. Scrolling video container into view using Playwright...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            try:
                await card_locator.scroll_into_view_if_needed(timeout=3000)
            except Exception:
                pass
            await self.page.wait_for_timeout(500)

            # Step 4: Hover over the relevant media/card element using Playwright
            logger.info("2. Hovering over video card element via Playwright hover()...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            try:
                await card_locator.hover(timeout=3000, force=True)
            except Exception as e:
                logger.debug(f"Playwright hover notice: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

            # Step 5: Wait approximately 1 second
            logger.info("3. Waiting ~1 second after hover...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            await asyncio.sleep(1.0)

            # Step 6: Click the relevant media/card element using Playwright
            logger.info("4. Clicking video card element via Playwright click()...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            try:
                # Target interactive element inside card if present, otherwise click card locator
                inner_btn = card_locator.locator("button, a, video, .purza-dl-btn, div[role='button']").first
                if await inner_btn.count() > 0:
                    await inner_btn.click(force=True, timeout=3000)
                else:
                    await card_locator.click(force=True, timeout=3000)
            except Exception as e:
                logger.warning(f"Playwright card click notice: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)

            # Give network and DOM 2 seconds to buffer/render
            await asyncio.sleep(2.0)
            return True

        except Exception as e:
            logger.warning(f"interact_with_video_card error: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=self.job_id)
            return False

    async def click_below_ready_message(self) -> bool:
        """Alias for interact_with_video_card — uses pure Playwright browser-level interaction."""
        return await self.interact_with_video_card()

    async def scroll_real_container(self, delta_y: int) -> dict:
        """
        Detects Dola's actual scrollable container (chat/messages/content element where scrollHeight > clientHeight),
        scrolls it by delta_y, records scrollTop before & after, and dispatches real wheel + scroll events.
        Returns dict with {initialTop, newTop, changed, container}.
        """
        try:
            res = await self.page.evaluate("""(deltaY) => {
                const isScrollable = (el) => {
                    if (!el) return false;
                    const overflowY = window.getComputedStyle(el).overflowY;
                    const isScrollStyle = overflowY === 'auto' || overflowY === 'scroll' || overflowY === 'overlay';
                    const hasScroll = (el.scrollHeight - el.clientHeight) > 5;
                    return isScrollStyle && hasScroll;
                };

                let target = null;
                // 1. Target selectors for chat/messages scroll container
                const selectors = [
                    '[class*="chat"]', '[class*="message"]', '[class*="content"]', '[class*="scroll"]',
                    'main', '[role="main"]', 'div[tabindex]'
                ];
                for (const sel of selectors) {
                    for (const el of document.querySelectorAll(sel)) {
                        if (isScrollable(el)) {
                            target = el;
                            break;
                        }
                    }
                    if (target) break;
                }

                // 2. Fallback: query all elements
                if (!target) {
                    for (const el of document.querySelectorAll('div, section, main, article')) {
                        if (isScrollable(el)) {
                            target = el;
                            break;
                        }
                    }
                }

                // 3. Fallback: window/document.scrollingElement
                if (!target) {
                    target = document.scrollingElement || document.documentElement || document.body;
                }

                const isWin = (target === document.body || target === document.documentElement || target === document.scrollingElement);
                const initialTop = isWin ? window.scrollY : target.scrollTop;

                // Dispatch synthetic wheel event to fire extension listeners
                try {
                    const wheelEvent = new WheelEvent('wheel', {
                        deltaY: deltaY,
                        deltaMode: 0,
                        bubbles: true,
                        cancelable: true,
                        view: window
                    });
                    target.dispatchEvent(wheelEvent);
                } catch (e) {}

                // Scroll the container
                if (isWin) {
                    window.scrollBy({ top: deltaY, behavior: 'instant' });
                } else {
                    target.scrollTop += deltaY;
                }

                // Dispatch scroll event
                try {
                    target.dispatchEvent(new Event('scroll', { bubbles: true }));
                } catch (e) {}

                const newTop = isWin ? window.scrollY : target.scrollTop;
                const containerName = target.tagName ? (target.tagName.toLowerCase() + (target.className ? '.' + String(target.className).split(' ')[0] : '')) : 'window';

                return {
                    initialTop: Math.round(initialTop),
                    newTop: Math.round(newTop),
                    changed: Math.abs(newTop - initialTop) > 0,
                    container: containerName
                };
            }""", delta_y)

            # Dual coverage: perform Playwright mouse wheel
            try:
                await self.page.mouse.wheel(0, delta_y)
            except Exception:
                pass

            return res
        except Exception as e:
            return {"initialTop": 0, "newTop": 0, "changed": False, "container": "error", "error": str(e)}

    async def execute_single_scroll_cycle(self, cycle_num: int) -> dict:
        """
        Executes 1 cycle of scroll container interaction:
        1. Scroll DOWN
        2. Wait 1s
        3. Scroll UP
        4. Wait 1s
        5. Scroll DOWN
        6. Wait 3.5s
        Measures scrollTop change on actual scroll container and logs compact result.
        """
        # 1. Scroll DOWN
        res_down1 = await self.scroll_real_container(350)
        await asyncio.sleep(1.0)

        # 2. Scroll UP
        res_up = await self.scroll_real_container(-150)
        await asyncio.sleep(1.0)

        # 3. Scroll DOWN again
        res_down2 = await self.scroll_real_container(300)

        start_top = res_down1.get("initialTop", 0)
        final_top = res_down2.get("newTop", 0)

        if res_down1.get("changed") or res_up.get("changed") or res_down2.get("changed"):
            scroll_str = f"scrollTop {start_top}→{final_top}"
        else:
            scroll_str = "SCROLL FAILED: scrollTop unchanged"

        logger.info(f"Cycle {cycle_num}: DOWN → UP → DOWN → {scroll_str} → checking download", category="WORKER", worker_id=self.worker_id)

        # Wait 3.5 seconds for Dola DOM & Purza extension to process viewport changes
        await asyncio.sleep(3.5)
        return {"start_top": start_top, "final_top": final_top}

    async def execute_viewport_scroll_sequence(self, sequence_num: int = 1) -> bool:
        """Alias for execute_single_scroll_cycle."""
        await self.execute_single_scroll_cycle(sequence_num)
        return True
