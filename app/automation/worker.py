"""
Tab-Based Multi-Generation Session Controller for Dola Bulk Video Automation.
Manages isolated Playwright browser sessions, handles Generate Videos skill workflow,
staggers multi-tab prompt submissions (5s delay), performs tab-level error recovery,
and coordinates job-isolated video download verification.
"""

import os
import time
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from playwright.async_api import async_playwright, Playwright, BrowserContext, Page, Download

from app.core.config import AppConfig
from app.core.database import db
from app.core.logger import logger, log_crash
from app.automation.browser_factory import BrowserFactory
from app.automation.dola_driver import DolaDriver
from app.automation.download_verifier import DownloadVerifier
from app.automation.watermark_remover import WatermarkRemover

class AutomationWorker:
    def __init__(self, worker_id: int, config: AppConfig, output_folder: str):
        self.worker_id = worker_id
        self.config = config
        self.output_folder = output_folder
        self.current_job: Optional[Dict[str, Any]] = None
        self.current_session: Optional[Dict[str, Any]] = None
        self.session_temp_folder: Optional[str] = None
        self.current_stage: str = "Idle"
        self.start_time: float = 0.0
        self.error: Optional[str] = None
        self._is_running: bool = False
        self.active_tabs_count: int = 0
        self.videos_completed_count: int = 0
        self.active_context = None

    def get_status_dict(self) -> Dict[str, Any]:
        """Returns live worker state dict for PyQt Dashboard UI."""
        elapsed = time.time() - self.start_time if self.start_time > 0 and self._is_running else 0
        return {
            "worker_id": self.worker_id,
            "stage": self.current_stage,
            "session_id": self.current_session.get("id") if self.current_session else None,
            "session_name": self.current_session.get("name", "N/A") if self.current_session else "N/A",
            "job_id": self.current_job.get("id", "N/A") if self.current_job else "N/A",
            "prompt_text": self.current_job.get("prompt_text", "N/A") if self.current_job else "N/A",
            "elapsed_seconds": int(elapsed),
            "error": self.error,
            "is_running": self._is_running,
            "active_tabs": self.active_tabs_count,
            "videos_completed": self.videos_completed_count
        }

    def bring_to_front(self):
        """Brings the active browser window / pages to front for live inspection."""
        try:
            if self.active_context and self.active_context.pages:
                page = self.active_context.pages[-1]
                logger.info(f"Focusing browser for Worker {self.worker_id} ({self.current_session.get('name') if self.current_session else ''})", category="WORKER", worker_id=self.worker_id)
        except Exception:
            pass

    def terminate_session(self):
        """Terminates this worker's current running session cleanly without stopping the entire queue."""
        logger.warning(f"Worker {self.worker_id} session termination requested by user.", category="WORKER", worker_id=self.worker_id)
        self._is_running = False
        self.current_stage = "Terminated"
        if self.current_session and self.current_session.get("id"):
            try:
                db.update_session_status(self.current_session["id"], "Available")
            except Exception:
                pass

    def stop(self):
        """Stops the worker immediately and cleans up active session status."""
        self._is_running = False
        self.current_stage = "Idle"
        if self.current_session and self.current_session.get("id"):
            sess_id = self.current_session["id"]
            try:
                latest_sess = db.get_session(sess_id)
                if latest_sess and latest_sess.get("status") == "Running":
                    db.update_session_status(sess_id, "Available")
            except Exception:
                pass

    async def run_job(self, job: Dict[str, Any], session: Dict[str, Any]) -> bool:
        """Backward-compatible wrapper executing a single job as a 1-item batch."""
        return await self.run_session_batch(session, [job])

    async def run_session_batch(self, session: Dict[str, Any], jobs: List[Dict[str, Any]]) -> bool:
        """
        Executes a batch of jobs (up to Videos Per Session) in ONE isolated Dola browser context.
        Implements Tab-Based Multi-Generation with Generate Videos skill and 5s stagger.
        """
        if not jobs:
            return True

        self.current_session = session
        self.current_job = jobs[0]
        self.start_time = time.time()
        self._is_running = True
        self.error = None
        self.active_tabs_count = 0
        self.videos_completed_count = 0

        session_id = session["id"]
        session_name = session["name"]
        total_jobs = len(jobs)

        logger.info(
            f"🚀 Worker {self.worker_id} starting session batch: '{session_name}' (Session ID: {session_id}, Workload: {total_jobs} prompts)",
            category="WORKER",
            worker_id=self.worker_id,
            session_name=session_name
        )
        db.update_session_status(session_id, "Running")

        playwright: Optional[Playwright] = None
        context: Optional[BrowserContext] = None
        tab_monitor_tasks: List[asyncio.Task] = []

        try:
            # ── 1. Launch Browser Context for this Session ──────────────────
            self.current_stage = "Launching Browser"
            playwright = await async_playwright().start()

            session_temp_dir = Path(tempfile.gettempdir()) / "dola_sessions" / f"sess_{session_id}_{int(time.time())}"
            session_temp_dir.mkdir(parents=True, exist_ok=True)
            self.session_temp_folder = str(session_temp_dir.resolve())

            context, first_page = await BrowserFactory.create_browser_context(
                playwright=playwright,
                session_info=session,
                extension_path=self.config.extension_path,
                headless=self.config.headless_mode,
                output_folder=self.session_temp_folder
            )
            self.active_context = context
            logger.info(f"Automation browser ready for Session '{session_name}'", category="BROWSER", worker_id=self.worker_id)

            # ── 2. Staggered Tab Launch Loop (5-Second Delay) ───────────────
            for idx, job in enumerate(jobs):
                if not self._is_running:
                    logger.warning(f"Automation stopped. Aborting remaining prompts for Session '{session_name}'.", category="WORKER", worker_id=self.worker_id)
                    break

                job_id = job["id"]
                self.current_job = job
                self.current_stage = f"Tab {idx+1}/{total_jobs} Starting"
                db.update_job_status(job_id, "Starting", worker_id=self.worker_id)

                logger.info(f"=== [TAB {idx+1}/{total_jobs}] Submitting Job '{job_id}' in Session '{session_name}' ===", category="WORKER", worker_id=self.worker_id, job_id=job_id)

                page: Page
                if idx == 0:
                    page = first_page
                else:
                    page = await context.new_page()

                self.active_tabs_count += 1

                # Start prompt generation on this specific tab (with automatic fresh tab retry)
                start_result = await self._start_prompt_on_tab(page, job, session)
                tab_retry = 0
                max_tab_retries = 2

                while start_result is False and tab_retry < max_tab_retries and self._is_running:
                    tab_retry += 1
                    logger.warning(f"JOB {job_id} | Tab {idx+1} start failed. Opening fresh tab to retry prompt (Attempt {tab_retry+1}/{max_tab_retries+1})...", category="WORKER", worker_id=self.worker_id, job_id=job_id)
                    try:
                        await page.close()
                    except Exception:
                        pass
                    await asyncio.sleep(2.0)
                    page = await context.new_page()
                    start_result = await self._start_prompt_on_tab(page, job, session)

                if start_result is True:
                    # Spawn independent background monitor task for this tab
                    task = asyncio.create_task(
                        self._monitor_tab_generation_and_download(context, page, job, session, attempt=1)
                    )
                    tab_monitor_tasks.append(task)
                    logger.info(f"JOB {job_id} | Generation start confirmed! Tab {idx+1} is generating in background.", category="WORKER", worker_id=self.worker_id, job_id=job_id)
                elif start_result in ("QUOTA_LIMIT_EXCEEDED", "SESSION_EXPIRED"):
                    is_expired = (start_result == "SESSION_EXPIRED")
                    reason = "Expired / Logged Out" if is_expired else "Daily Limit Exceeded"
                    self.current_stage = f"Session {reason}"
                    logger.error(f"🚨 [{start_result}] Session '{session_name}' is {reason}. Triggering auto-failover...", category="WORKER", worker_id=self.worker_id)
                    db.make_session_expired(session_id)

                    # Gather all remaining jobs in this session workload (current job + unstarted ones)
                    remaining_job_ids = [j["id"] for j in jobs[idx:]]

                    # Dynamically transfer prompts to next available working session
                    failover_sess = db.failover_session_jobs(session_id, remaining_job_ids)
                    if failover_sess:
                        logger.info(
                            f"🔄 [AUTO_FAILOVER] Transferred {len(remaining_job_ids)} prompt(s) from Session '{session_name}' to Session '{failover_sess['name']}'. Will continue execution seamlessly in queue!",
                            category="WORKER",
                            worker_id=self.worker_id
                        )
                    else:
                        logger.warning(
                            f"⚠️ No other available sessions found in pool to take over {len(remaining_job_ids)} prompt(s).",
                            category="WORKER",
                            worker_id=self.worker_id
                        )
                        for r_jid in remaining_job_ids:
                            db.update_job_status(r_jid, "Failed", error_message=f"Session '{session_name}' {reason} and no alternative active sessions found.")

                    if len(context.pages) > 1:
                        try:
                            await page.close()
                        except Exception:
                            pass
                    self.active_tabs_count = max(0, self.active_tabs_count - 1)
                    break
                else:
                    logger.error(f"JOB {job_id} | Failed to confirm generation start on Tab {idx+1} after retries.", category="WORKER", worker_id=self.worker_id, job_id=job_id)
                    db.update_job_status(job_id, "Failed", error_message="Generation confirmation or start failed.")
                    if len(context.pages) > 1:
                        try:
                            await page.close()
                        except Exception:
                            pass
                    self.active_tabs_count = max(0, self.active_tabs_count - 1)

                # Wait 5 seconds before creating the next tab if more prompts remain
                if idx < total_jobs - 1 and self._is_running:
                    logger.info(f"Waiting {self.config.tab_launch_delay_sec}s before launching next prompt tab...", category="WORKER", worker_id=self.worker_id)
                    await asyncio.sleep(self.config.tab_launch_delay_sec)

            # ── 3. Await All Tab Monitors in this Session ───────────────────
            if tab_monitor_tasks:
                self.current_stage = "Monitoring Active Generations"
                logger.info(f"Waiting for {len(tab_monitor_tasks)} active generation tabs to complete...", category="WORKER", worker_id=self.worker_id)
                await asyncio.gather(*tab_monitor_tasks, return_exceptions=True)

            # Check actual job outcome counts for this session batch
            sess_jobs = [db.get_job(j["id"]) for j in jobs]
            done_count = sum(1 for j in sess_jobs if j and j.get("status") == "Completed")
            fail_count = sum(1 for j in sess_jobs if j and j.get("status") == "Failed")

            # Deduct remaining videos count for this session
            if done_count > 0:
                rem_videos = db.deduct_session_videos_left(session_id, done_count)
                logger.info(f"📊 Session '{session_name}' finished {done_count} videos. Remaining quota: {rem_videos} videos left.", category="WORKER", worker_id=self.worker_id)

            latest_sess = db.get_session(session_id)
            if latest_sess and latest_sess.get("status") == "Expired":
                self.current_stage = "Session Expired / Login Required"
                logger.error(f"❌ Session '{session_name}' ended with Expired status. Please log in again.", category="WORKER", worker_id=self.worker_id)
                return False
            elif fail_count > 0 and done_count == 0:
                self.current_stage = "Failed"
                logger.error(f"❌ Session '{session_name}' finished with {fail_count} failed prompt(s).", category="WORKER", worker_id=self.worker_id)
            elif fail_count > 0:
                self.current_stage = "Partial Failure"
                logger.warning(f"⚠️ Session '{session_name}' finished: {done_count} completed, {fail_count} failed.", category="WORKER", worker_id=self.worker_id)
            else:
                self.current_stage = "Completed"
                logger.info(f"✅ Session '{session_name}' finished all {done_count} assigned prompts cleanly!", category="WORKER", worker_id=self.worker_id)

            if latest_sess and latest_sess.get("status") != "Expired":
                db.update_session_status(session_id, "Available")
            return done_count > 0

        except Exception as e:
            self.error = str(e)
            self.current_stage = "Failed"
            log_crash(f"SessionWorker {self.worker_id} Session '{session_name}'", e)
            logger.error(f"Worker {self.worker_id} Session batch encountered error: {e}", category="WORKER", worker_id=self.worker_id)
            db.update_session_status(session_id, "Error", error_count_delta=1)
            return False

        finally:
            # Cleanly release browser resources for this session
            self._is_running = False
            self.active_tabs_count = 0
            self.active_context = None
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            if playwright:
                try:
                    await playwright.stop()
                except Exception:
                    pass

            try:
                latest_sess = db.get_session(session_id)
                if latest_sess and latest_sess.get("status") == "Running":
                    db.update_session_status(session_id, "Available")
            except Exception:
                pass

    async def _start_prompt_on_tab(self, page: Page, job: Dict[str, Any], session: Dict[str, Any]) -> Any:
        """
        Navigates a single tab to Dola /chat, triggers New Chat -> Fast -> Pro -> Skills -> Generate Videos,
        submits the prompt, and confirms generation start.
        Returns True on success, "SESSION_EXPIRED" if session logged out, or False on other failure.
        """
        job_id = job["id"]
        session_id = session.get("id")
        session_name = session.get("name", f"Session {session_id}")
        driver = DolaDriver(page, worker_id=self.worker_id, job_id=job_id)

        try:
            # 1. Open Dola /chat
            if not await driver.open_dola():
                logger.error(f"JOB {job_id} | Failed to load https://www.dola.com/chat", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=job_id)
                return False

            # 1.5 Verify Login Authentication
            is_logged_in, login_reason = await driver.verify_login()
            if not is_logged_in:
                logger.error(
                    f"🚨 [SESSION_LOGGED_OUT] Session '{session_name}' (ID: {session_id}) is LOGGED OUT! ({login_reason}). Dola modal/button detected on screen.",
                    category="WORKER",
                    worker_id=self.worker_id,
                    job_id=job_id
                )
                db.make_session_expired(session_id)
                db.update_job_status(job_id, "Failed", error_message=f"Session Expired: {login_reason}")
                return "SESSION_EXPIRED"

            # 2. Click New Chat inside this tab
            await driver.click_new_chat()

            # 3. Switch composer from Fast to Pro mode
            if not await driver.switch_to_pro_mode():
                # Check if failure was due to session logout
                is_logged_in, login_reason = await driver.verify_login()
                if not is_logged_in:
                    logger.error(f"🚨 [SESSION_LOGGED_OUT] Session '{session_name}' is logged out during Pro mode switch ({login_reason}). Marking as Expired.", category="WORKER", worker_id=self.worker_id, job_id=job_id)
                    db.make_session_expired(session_id)
                    db.update_job_status(job_id, "Failed", error_message=f"Session Expired: {login_reason}")
                    return "SESSION_EXPIRED"
                logger.error(f"JOB {job_id} | Pro mode could not be activated or verified. Aborting tab submission.", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=job_id)
                return False

            # 4. Select 'Generate Videos' Skill (Skills -> scroll -> Generate Videos -> verify)
            if not await driver.select_generate_videos_skill():
                # Check if failure was due to session logout
                is_logged_in, login_reason = await driver.verify_login()
                if not is_logged_in:
                    logger.error(f"🚨 [SESSION_LOGGED_OUT] Session '{session_name}' is logged out during Skills selection ({login_reason}). Marking as Expired.", category="WORKER", worker_id=self.worker_id, job_id=job_id)
                    db.make_session_expired(session_id)
                    db.update_job_status(job_id, "Failed", error_message=f"Session Expired: {login_reason}")
                    return "SESSION_EXPIRED"
                logger.error(f"JOB {job_id} | Generate Videos skill could not be selected or verified. Aborting tab submission.", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=job_id)
                return False

            # 5. Paste & Submit Prompt (with exact prompt length & content verification)
            logger.info(f"JOB {job_id} | Pasting prompt into Generate Videos composer...", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=job_id)
            if not await driver.submit_prompt(job["prompt_text"]):
                logger.error(f"JOB {job_id} | Prompt paste verification failed. Aborting submission.", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=job_id)
                return False

            # 6. Dynamic Response Handling & Generation Start Confirmation
            status, text = await driver.handle_dynamic_dola_response(timeout_sec=120.0)
            if status in ("GENERATION_STARTED", "COMPLETED"):
                db.update_job_status(job_id, "GENERATING")
                return True
            elif status == "QUOTA_LIMIT_EXCEEDED":
                return "QUOTA_LIMIT_EXCEEDED"
            elif status == "TRUE_ERROR":
                logger.warning(f"JOB {job_id} | Dola reported error on submission: '{text}'", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=job_id)
                return False
            else:
                # If timeout or ambiguous, check if start phrases exist or if no error occurred
                ctype, ctext = await driver.classify_dola_response()
                if ctype == "QUOTA_LIMIT_EXCEEDED":
                    return "QUOTA_LIMIT_EXCEEDED"
                elif ctype in ("VALID_GENERATION", "COMPLETED"):
                    db.update_job_status(job_id, "GENERATING")
                    return True
                elif ctype != "UNEXPECTED_ERROR":
                    logger.info(f"JOB {job_id} | Prompt submitted with no error on page. Transitioning to generation monitoring.", category="WORKER", worker_id=self.worker_id, job_id=job_id)
                    db.update_job_status(job_id, "GENERATING")
                    return True

            return False
        except Exception as e:
            logger.error(f"JOB {job_id} | _start_prompt_on_tab failed: {e}", category="DOLA_DRIVER", worker_id=self.worker_id, job_id=job_id)
            return False

    async def _monitor_tab_generation_and_download(
        self,
        context: BrowserContext,
        page: Page,
        job: Dict[str, Any],
        session: Dict[str, Any],
        attempt: int = 1
    ) -> bool:
        """
        Monitors an individual tab until video generation completes or fails.
        On video ready: runs download pipeline, verifies MP4, and closes only this tab.
        On true error: closes this tab, opens a NEW tab in the same context, and retries the prompt.
        """
        job_id = job["id"]
        session_id = session["id"]
        session_name = session["name"]
        MAX_RETRIES = 2
        total_attempts = MAX_RETRIES + 1

        # Per-job isolated temp download directory
        job_temp_dir = Path(tempfile.gettempdir()) / "dola_downloads" / f"job_{job_id}"
        job_temp_dir.mkdir(parents=True, exist_ok=True)
        job_temp_folder = str(job_temp_dir.resolve())

        # Register tab-level download listener to ensure page downloads save directly to job_temp_folder
        async def _on_tab_download(download: Download):
            try:
                dest = str(Path(job_temp_folder) / f"page_dl_{int(time.time()*1000)}.mp4")
                await download.save_as(dest)
                logger.info(f"JOB {job_id} | Intercepted tab download saved to: {dest}", category="DOWNLOAD", worker_id=self.worker_id, job_id=job_id)
            except Exception as dl_err:
                logger.warning(f"JOB {job_id} | Tab download save notice: {dl_err}", category="DOWNLOAD", worker_id=self.worker_id, job_id=job_id)

        page.on("download", _on_tab_download)

        driver = DolaDriver(page, worker_id=self.worker_id, job_id=job_id)
        driver.setup_network_media_interceptor(job_temp_folder)

        gen_start_time = time.time()
        video_ready = False
        last_progress_log = 0.0

        try:
            logger.info(f"⏳ JOB {job_id} | Generation in progress on Tab... Waiting for Dola completion.", category="WORKER", worker_id=self.worker_id, job_id=job_id)

            while time.time() - gen_start_time < self.config.generation_timeout_sec:
                if not self._is_running:
                    break

                elapsed_sec = int(time.time() - gen_start_time)
                if time.time() - last_progress_log >= 30.0:
                    last_progress_log = time.time()
                    logger.info(f"⏳ JOB {job_id} | Tab generating ({elapsed_sec}s elapsed)...", category="WORKER", worker_id=self.worker_id, job_id=job_id)

                # Check for Completion or True Error
                ctype, ctext = await driver.classify_dola_response()

                if ctype == "UNEXPECTED_ERROR":
                    logger.warning(f"JOB {job_id} | Unexpected Dola error detected on tab: \"{ctext}\"", category="WORKER", worker_id=self.worker_id, job_id=job_id)
                    raise RuntimeError(f"DOLA_UNEXPECTED_ERROR: {ctext}")

                elif ctype == "COMPLETED" or await driver.check_current_job_download_button(None):
                    video_ready = True
                    logger.info(f"🎉 JOB {job_id} | Dola video ready! Starting download pipeline...", category="WORKER", worker_id=self.worker_id, job_id=job_id)
                    break

                await asyncio.sleep(self.config.polling_interval_sec)

            if not video_ready:
                raise TimeoutError(f"Video generation timed out after {self.config.generation_timeout_sec}s")

            # ── 4. Execute Proven Video Download Pipeline (Same Tab Retries) ──
            db.update_job_status(job_id, "DOWNLOADING")
            verified_file = None

            search_dirs = [job_temp_folder]
            if self.session_temp_folder:
                search_dirs.append(self.session_temp_folder)

            for dl_attempt in range(1, 4):
                try:
                    logger.info(f"JOB {job_id} | Video download extraction attempt {dl_attempt}/3...", category="DOWNLOAD", worker_id=self.worker_id, job_id=job_id)

                    # Step A: Initialize lazy-loaded video card
                    await driver.initialize_lazy_video_block()

                    # Step B: Fast context request download
                    fast_dl = await driver.fast_download_via_context_request(job_temp_folder)
                    if fast_dl:
                        logger.info(f"JOB {job_id} | Fast context download captured: {fast_dl}", category="DOWNLOAD", worker_id=self.worker_id, job_id=job_id)

                    # Step C: Smart extraction & direct video fetching
                    await driver.trigger_smart_download_extraction(job_temp_folder)

                    # Step D: Click video download button
                    await driver.click_download_button()

                    # Step E: Verify MP4 in job-isolated download directory + session temp dirs
                    verifier = DownloadVerifier(
                        download_dir=job_temp_folder,
                        timeout_sec=15.0 if dl_attempt < 3 else self.config.download_verification_timeout_sec,
                        worker_id=self.worker_id,
                        job_id=job_id,
                        additional_dirs=search_dirs
                    )
                    verified_file = await verifier.verify_download()

                    if verified_file and verified_file.exists():
                        break
                    else:
                        logger.warning(f"JOB {job_id} | Download attempt {dl_attempt}/3 not ready, retrying on same tab...", category="DOWNLOAD", worker_id=self.worker_id, job_id=job_id)
                        await asyncio.sleep(2.0)
                except Exception as dl_err:
                    logger.warning(f"JOB {job_id} | Download extraction attempt {dl_attempt} error: {dl_err}", category="DOWNLOAD", worker_id=self.worker_id, job_id=job_id)
                    await asyncio.sleep(2.0)

            if not verified_file or not verified_file.exists():
                logger.error(f"❌ JOB {job_id} | Video was generated successfully, but MP4 download failed after 3 attempts. Will NOT retry generation to save credits.", category="WORKER", worker_id=self.worker_id, job_id=job_id)
                db.update_job_status(job_id, "Failed", error_message="Video generated successfully on Dola, but MP4 download extraction failed.")
                return False

            file_size = verified_file.stat().st_size
            logger.info(f"✅ JOB {job_id} | MP4 Verified: {verified_file.name} ({file_size / (1024*1024):.2f} MB)", category="DOWNLOAD", worker_id=self.worker_id, job_id=job_id)

            # ── 5. Watermark Removal & Move to Final Output Folder ───────────
            out_dir = Path(self.output_folder)
            out_dir.mkdir(parents=True, exist_ok=True)
            final_mp4_path = out_dir / f"{job_id}.mp4"

            wm_applied = False
            if getattr(self.config, "enable_watermark_remover", True):
                try:
                    bx = getattr(self.config, "blur_x", 540)
                    by = getattr(self.config, "blur_y", 1220)
                    bw = getattr(self.config, "blur_w", 170)
                    bh = getattr(self.config, "blur_h", 50)
                    logger.info(f"🧼 JOB {job_id} | Applying Watermark Blur (X={bx}, Y={by}, W={bw}, H={bh})...", category="DOWNLOAD", worker_id=self.worker_id, job_id=job_id)
                    wm_applied = WatermarkRemover.remove_watermark(
                        input_mp4=str(verified_file),
                        output_mp4=str(final_mp4_path),
                        x=bx,
                        y=by,
                        w=bw,
                        h=bh
                    )
                except Exception as wm_err:
                    logger.warning(f"JOB {job_id} | Watermark blur notice: {wm_err}", category="DOWNLOAD", worker_id=self.worker_id, job_id=job_id)

            if not wm_applied:
                if str(verified_file.resolve()) != str(final_mp4_path.resolve()):
                    shutil.move(str(verified_file), str(final_mp4_path))
                logger.info(f"📁 JOB {job_id} | Saved to output folder: {final_mp4_path}", category="DOWNLOAD", worker_id=self.worker_id, job_id=job_id)
            else:
                if verified_file.exists() and str(verified_file.resolve()) != str(final_mp4_path.resolve()):
                    try:
                        os.remove(str(verified_file))
                    except Exception:
                        pass
                logger.info(f"📁 JOB {job_id} | Clean watermark-free video saved to: {final_mp4_path}", category="DOWNLOAD", worker_id=self.worker_id, job_id=job_id)

            file_size = final_mp4_path.stat().st_size if final_mp4_path.exists() else file_size

            # Mark completed in DB
            db.update_job_status(
                job_id=job_id,
                status="Completed",
                downloaded_filename=final_mp4_path.name,
                downloaded_filepath=str(final_mp4_path.resolve()),
                downloaded_filesize=file_size
            )
            self.videos_completed_count += 1

            # Auto-remove completed prompt from queue
            prompt_id = job.get("prompt_id")
            if prompt_id:
                try:
                    db.remove_completed_prompt(prompt_id)
                    logger.info(f"🗑️ Completed prompt #{prompt_id} automatically removed from queue.", category="QUEUE", worker_id=self.worker_id, job_id=job_id)
                except Exception as rem_err:
                    logger.warning(f"Notice auto-removing prompt #{prompt_id}: {rem_err}", category="QUEUE")

            # Cloud SaaS Telemetry Sync (Async non-blocking)
            try:
                from app.core.cloud_manager import cloud_manager
                cloud_manager.log_video_event(
                    video_name=final_mp4_path.name,
                    file_size_mb=file_size / (1024 * 1024)
                )
            except Exception as cloud_err:
                logger.warning(f"Cloud activity sync notice: {cloud_err}", category="WORKER", worker_id=self.worker_id)

            # Clean up temp folder
            try:
                shutil.rmtree(job_temp_folder, ignore_errors=True)
            except Exception:
                pass

            # Update session credits if visible
            try:
                await driver.extract_and_update_credits(session_id)
            except Exception:
                pass

            return True

        except Exception as e:
            err_msg = str(e)
            logger.warning(f"JOB {job_id} | Tab generation error encountered: {err_msg}", category="WORKER", worker_id=self.worker_id, job_id=job_id)

            # ── TAB-LEVEL ERROR RECOVERY (Only if video was NOT yet ready) ───
            if not video_ready and attempt < total_attempts:
                next_attempt = attempt + 1
                logger.warning(f"JOB {job_id} | Unexpected Dola generation response detected: \"{err_msg}\"", category="WORKER", worker_id=self.worker_id, job_id=job_id)
                logger.warning(f"JOB {job_id} | Closing failed tab and opening fresh tab in SAME session (Attempt {next_attempt}/{total_attempts})", category="WORKER", worker_id=self.worker_id, job_id=job_id)
                logger.warning(f"JOB {job_id} | Reusing original prompt: \"{job['prompt_text'][:60]}...\"", category="WORKER", worker_id=self.worker_id, job_id=job_id)

                # Close failed tab
                try:
                    await page.close()
                except Exception:
                    pass

                # Open fresh tab in SAME browser context
                try:
                    new_tab = await context.new_page()
                    start_ok = await self._start_prompt_on_tab(new_tab, job, session)
                    if start_ok is True:
                        return await self._monitor_tab_generation_and_download(
                            context, new_tab, job, session, attempt=next_attempt
                        )
                    elif start_ok == "SESSION_EXPIRED":
                        self.current_stage = "Session Expired / Login Required"
                        logger.error(f"❌ Session '{session_name}' is EXPIRED. Aborting tab retry.", category="WORKER", worker_id=self.worker_id, job_id=job_id)
                        db.update_job_status(job_id, "Failed", error_message="Session Expired / Login Required")
                        return False
                except Exception as retry_err:
                    logger.error(f"JOB {job_id} | Tab retry launch failed: {retry_err}", category="WORKER", worker_id=self.worker_id, job_id=job_id)

            # Retries exhausted
            db.update_job_status(job_id, "Failed", error_message=err_msg)
            return False

        finally:
            # Always close this specific tab upon completion/failure
            try:
                await page.close()
            except Exception:
                pass
            self.active_tabs_count = max(0, self.active_tabs_count - 1)
