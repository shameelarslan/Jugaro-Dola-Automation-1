"""
Async Queue Orchestrator & Rolling Session Pool Controller.
Manages concurrent Dola browser workers ('Sessions At A Time'),
assigns batches of prompts per session ('Videos Per Session'),
and coordinates tab-based generation lifecycles, retries, pause, and stop controls.
"""

import asyncio
import threading
import time
import traceback
from typing import List, Dict, Any, Optional, Callable
from app.core.config import AppConfig
from app.core.database import db
from app.core.logger import logger, log_crash
from app.automation.worker import AutomationWorker
from app.core.admin_manager import admin_manager

class QueueManager:
    def __init__(self, config: AppConfig):
        self.config = config
        self.active_run_id: Optional[str] = None
        self.output_folder: str = config.default_download_dir
        self.concurrency_limit: int = config.sessions_at_a_time
        
        self._is_running: bool = False
        self._is_paused: bool = False
        self._stop_requested: bool = False
        
        self.workers: List[AutomationWorker] = []
        self._worker_slots: List[bool] = []
        self._bg_thread: Optional[threading.Thread] = None
        self._status_callbacks: List[Callable[[], None]] = []
        
        logger.info("Automation Queue Manager initialized", category="QUEUE")

    def register_status_callback(self, callback: Callable[[], None]):
        if callback not in self._status_callbacks:
            self._status_callbacks.append(callback)

    def notify_status_change(self):
        for cb in self._status_callbacks:
            try:
                cb()
            except Exception:
                pass

    def prepare_and_start_automation(self, prompts: List[Dict[str, Any]], sessions: List[Dict[str, Any]]) -> str:
        """
        Groups prompts into session workloads based on 'Videos Per Session'
        and starts the rolling session pool with up to 'Sessions At A Time' concurrency.
        """
        if not prompts:
            raise ValueError("No prompts available to start automation.")
        if not sessions:
            raise ValueError("No sessions available to start automation.")

        # Reload configuration
        self.config = db.load_app_config()
        self.output_folder = self.config.default_download_dir
        self.concurrency_limit = max(1, min(50, self.config.sessions_at_a_time))
        videos_per_session = max(1, min(15, self.config.videos_per_session))

        run_id = f"RUN_{int(time.time())}"
        self.active_run_id = run_id

        # HARD PER-SESSION LIMIT & CAPACITY:
        # Current Capacity = Selected Sessions × Videos Per Session
        # Each selected session gets at most 1 workload slice of max `videos_per_session` prompts.
        # Excess prompts beyond current capacity remain Pending in DB for future session runs.
        num_sessions = len(sessions)
        capacity = num_sessions * videos_per_session
        prompts_to_process = prompts[:capacity]
        remaining_prompts_count = len(prompts) - len(prompts_to_process)

        # Clean up any stale non-completed jobs for these prompts to prevent job duplication
        prompt_ids = [p["id"] for p in prompts_to_process]
        if prompt_ids:
            with db.get_connection() as conn:
                placeholders = ",".join("?" * len(prompt_ids))
                conn.cursor().execute(f"DELETE FROM jobs WHERE prompt_id IN ({placeholders}) AND status != 'Completed'", prompt_ids)
                conn.commit()

        prompt_idx = 0
        assigned_jobs_count = 0
        for s_idx, session in enumerate(sessions):
            start_offset = s_idx * videos_per_session
            end_offset = start_offset + videos_per_session
            chunk = prompts_to_process[start_offset:end_offset]
            if not chunk:
                break
            for p in chunk:
                prompt_idx += 1
                assigned_jobs_count += 1
                job_number = f"WaqasAutomation_{run_id}_{prompt_idx:03d}"
                db.add_job(
                    job_id=job_number,
                    batch_id=run_id,
                    prompt_id=p["id"],
                    session_id=session["id"]
                )

        if remaining_prompts_count > 0:
            logger.info(
                f"ℹ️ Capacity limit ({capacity} videos = {num_sessions} sessions × {videos_per_session} VPS). "
                f"{remaining_prompts_count} prompt(s) will remain pending for the next available session cycle.",
                category="QUEUE"
            )

        # Initialize worker instances for Sessions At A Time slots
        num_workers = min(self.concurrency_limit, num_sessions, max(1, (assigned_jobs_count + videos_per_session - 1) // videos_per_session))
        self.workers = [AutomationWorker(i + 1, self.config, self.output_folder) for i in range(num_workers)]
        self._worker_slots = [False] * num_workers
        
        self._is_running = True
        self._is_paused = False
        self._stop_requested = False

        logger.info(
            f"🎬 Started Rolling Session Automation (Run: {run_id}, Sessions At A Time: {self.concurrency_limit}, "
            f"Videos Per Session: {videos_per_session}, Prompts Assigned: {assigned_jobs_count}/{len(prompts)}, "
            f"Output: {self.output_folder})",
            category="QUEUE"
        )

        def run_thread_loop():
            loop = None
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                def _loop_exc_handler(lp, context):
                    exc = context.get("exception")
                    msg = context.get("message", "(no message)")
                    if exc and not isinstance(exc, (asyncio.CancelledError, GeneratorExit)):
                        log_crash(f"asyncio background loop exception: {msg}", exc)
                        logger.error(f"ASYNC BACKGROUND EXCEPTION: {msg} | {exc}", category="QUEUE")

                loop.set_exception_handler(_loop_exc_handler)
                loop.run_until_complete(self._dispatch_loop())
            except BaseException as ex:
                log_crash("QueueManager Background Thread", ex)
                logger.error(f"Fatal exception in queue thread: {ex}\n{traceback.format_exc()}", category="QUEUE")
            finally:
                try:
                    if loop and not loop.is_closed():
                        loop.close()
                except Exception:
                    pass
                self._is_running = False
                logger.info("Automation queue thread closed cleanly.", category="QUEUE")
                self.notify_status_change()

        self._bg_thread = threading.Thread(target=run_thread_loop, daemon=True, name="DolaQueueThread")
        self._bg_thread.start()
        return run_id

    def pause_automation(self):
        """Pauses worker dispatch. Active session tabs continue their current generation."""
        if self._is_running:
            self._is_paused = True
            logger.info("⏸️ Automation paused. Active generation tabs will finish safely.", category="QUEUE")
            self.notify_status_change()

    def resume_automation(self):
        """Resumes worker dispatch."""
        if self._is_running and self._is_paused:
            self._is_paused = False
            logger.info("▶️ Automation resumed.", category="QUEUE")
            self.notify_status_change()

    def stop_automation(self):
        """Stops automation immediately and resets all running sessions to Available."""
        self._stop_requested = True
        self._is_running = False
        for w in self.workers:
            w.stop()
            w._is_running = False
            w.current_stage = "Idle"

        # Cleanly reset any sessions in Running status back to Available and non-completed jobs to Stopped
        try:
            with db.get_connection() as conn:
                conn.cursor().execute("UPDATE sessions SET status = 'Available' WHERE status = 'Running'")
                conn.cursor().execute("UPDATE jobs SET status = 'Stopped' WHERE status NOT IN ('Completed', 'Failed')")
                conn.commit()
        except Exception:
            pass

        logger.info("⏹️ Automation stopped cleanly by user. All active sessions reset to Available.", category="QUEUE")
        self.notify_status_change()

    def terminate_worker_session(self, worker_id: int):
        """Terminates a specific worker's running session cleanly, allowing the rolling pool to continue with remaining sessions."""
        for w in self.workers:
            if w.worker_id == worker_id:
                w.terminate_session()
                logger.info(f"Worker {worker_id} session terminated independently by user.", category="QUEUE")
                self.notify_status_change()
                break

    def open_worker_session(self, worker_id: int):
        """Focuses the active browser window / pages for a specific worker."""
        for w in self.workers:
            if w.worker_id == worker_id:
                w.bring_to_front()
                break

    def retry_failed_jobs(self):
        """Resets failed jobs back to Pending state."""
        if self.active_run_id:
            db.reset_failed_jobs(self.active_run_id)
            logger.info("🔄 Reset failed jobs to Pending.", category="QUEUE")
            self.notify_status_change()

    def clear_queue_and_dashboard(self):
        """Stops active automation and clears all jobs from DB and dashboard."""
        self.stop_automation()
        self.active_run_id = None
        db.clear_all_jobs()
        admin_manager.reset_job_stages()
        for w in self.workers:
            w._is_running = False
            w.current_stage = "Idle"

        try:
            with db.get_connection() as conn:
                conn.cursor().execute("UPDATE sessions SET status = 'Available' WHERE status = 'Running'")
                conn.commit()
        except Exception:
            pass

        logger.info("🧹 Dashboard queue and job history cleared.", category="QUEUE")
        self.notify_status_change()

    def get_live_worker_states(self) -> List[Dict[str, Any]]:
        """Returns live worker states for UI Dashboard rendering."""
        return [w.get_status_dict() for w in self.workers]

    def get_batch_summary_stats(self) -> Dict[str, int]:
        """Returns overview counter metrics for Dashboard, scoped to active run if active."""
        if self.active_run_id:
            jobs = db.get_batch_jobs(self.active_run_id)
        else:
            jobs = db.get_all_jobs()

        if not jobs:
            return {"total": 0, "running": 0, "completed": 0, "pending": 0, "failed": 0, "active_sessions": 0, "downloaded": 0}

        total = len(jobs)
        completed = sum(1 for j in jobs if j["status"] == "Completed")
        failed = sum(1 for j in jobs if j["status"] == "Failed")
        running = sum(1 for j in jobs if j["status"] not in ("Pending", "Completed", "Failed"))
        pending = sum(1 for j in jobs if j["status"] == "Pending")
        active_sessions = sum(1 for w in self.workers if w._is_running)

        return {
            "total": total,
            "running": running,
            "completed": completed,
            "pending": pending,
            "failed": failed,
            "active_sessions": active_sessions,
            "downloaded": completed
        }

    async def _dispatch_loop(self):
        """
        Main async loop feeding available session worker slots with session workloads.
        Implements rolling session pool.
        """
        semaphore = asyncio.Semaphore(len(self.workers))

        async def session_worker_wrapper(worker: AutomationWorker, slot_index: int, session: Dict[str, Any], session_jobs: List[Dict[str, Any]]):
            async with semaphore:
                self._worker_slots[slot_index] = True
                self.notify_status_change()
                try:
                    await worker.run_session_batch(session, session_jobs)
                except asyncio.CancelledError:
                    logger.warning(f"Worker {worker.worker_id} cancelled.", category="WORKER", worker_id=worker.worker_id)
                except BaseException as ex:
                    log_crash(f"SessionWorker {worker.worker_id} (BaseException)", ex)
                    logger.error(f"FATAL EXCEPTION in SessionWorker {worker.worker_id}: {ex}\n{traceback.format_exc()}", category="WORKER", worker_id=worker.worker_id)
                    for j in session_jobs:
                        try:
                            db.update_job_status(j["id"], "Failed", error_message=str(ex))
                        except Exception:
                            pass
                finally:
                    self._worker_slots[slot_index] = False
                    worker._is_running = False
                    self.notify_status_change()

        while self._is_running and not self._stop_requested:
            if self._is_paused:
                await asyncio.sleep(1.0)
                continue

            try:
                # Fetch pending jobs grouped by session
                jobs = db.get_all_jobs()
                pending_jobs = [j for j in jobs if j["status"] == "Pending"]

                if not pending_jobs:
                    active_count = sum(1 for w in self.workers if w._is_running)
                    if active_count == 0:
                        stats = self.get_batch_summary_stats()
                        done_c = stats.get("completed", 0)
                        fail_c = stats.get("failed", 0)
                        if fail_c > 0 and done_c == 0:
                            logger.error(f"❌ Automation finished with {fail_c} failed prompt(s).", category="QUEUE")
                        elif fail_c > 0:
                            logger.warning(f"⚠️ Automation finished: {done_c} completed, {fail_c} failed.", category="QUEUE")
                        else:
                            logger.info(f"🎉 All {done_c} prompt automation jobs completed successfully!", category="QUEUE")
                        self._is_running = False
                        break
                    await asyncio.sleep(2.0)
                    continue

                # Find available worker slot
                slot_idx = -1
                for idx, busy in enumerate(self._worker_slots):
                    if not busy and not self.workers[idx]._is_running:
                        slot_idx = idx
                        break

                if slot_idx != -1:
                    # Pick next session that has pending jobs
                    # Get distinct session_ids of pending jobs
                    pending_session_ids = list(dict.fromkeys(j["session_id"] for j in pending_jobs))
                    
                    # Find a session_id that is NOT currently being processed by another running worker
                    running_session_ids = [w.current_session["id"] for w in self.workers if w._is_running and w.current_session]
                    target_session_id = next((sid for sid in pending_session_ids if sid not in running_session_ids), None)

                    if target_session_id is not None:
                        session_info = db.get_session(target_session_id)
                        session_pending_jobs = [j for j in pending_jobs if j["session_id"] == target_session_id]

                        if session_info and session_pending_jobs:
                            worker = self.workers[slot_idx]
                            logger.info(
                                f"Assigning Session '{session_info['name']}' ({len(session_pending_jobs)} prompts) to Worker {worker.worker_id}",
                                category="QUEUE"
                            )
                            asyncio.create_task(
                                session_worker_wrapper(worker, slot_idx, session_info, session_pending_jobs)
                            )
                            await asyncio.sleep(3.0)
                            continue

            except Exception as ex:
                logger.error(f"Error in queue dispatch loop: {ex}\n{traceback.format_exc()}", category="QUEUE")

            await asyncio.sleep(2.0)
