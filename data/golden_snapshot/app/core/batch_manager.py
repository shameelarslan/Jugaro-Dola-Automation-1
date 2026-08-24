"""
Batch Manager for Batch Creation, Output Directory Resolution, 1:1 Auto-Mapping, and History.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from app.core.database import db
from app.core.config import AppConfig
from app.core.logger import logger

class BatchManager:
    @staticmethod
    def create_new_batch(
        name: str,
        prompts: List[Dict[str, Any]],
        sessions: List[Dict[str, Any]],
        output_folder: str,
        separate_batch_folders: bool = True,
        concurrency_limit: int = 5,
        preset_name: str = "TikTok 9:16 10s",
        assignment_mode: str = "one_to_one"
    ) -> Tuple[str, str, List[Dict[str, Any]]]:
        """
        Creates a new Batch and maps prompts to sessions 1:1 automatically.
        Returns Tuple[batch_id, resolved_output_folder, jobs_list].
        """
        if not prompts:
            raise ValueError("Cannot create batch without prompts.")
        if not sessions:
            raise ValueError("Cannot create batch without sessions.")

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_id = f"BATCH_{timestamp_str}"
        clean_name = name.strip() or f"Batch {timestamp_str}"

        # Resolve output folder path
        base_output = Path(output_folder)
        if separate_batch_folders:
            resolved_output = base_output / clean_name.replace(" ", "_")
        else:
            resolved_output = base_output

        resolved_output.mkdir(parents=True, exist_ok=True)
        resolved_output_str = str(resolved_output.resolve())

        # Create batch entry in SQLite
        db.create_batch(
            batch_id=batch_id,
            name=clean_name,
            preset_name=preset_name,
            output_folder=resolved_output_str,
            separate_batch_folders=separate_batch_folders,
            concurrency_limit=concurrency_limit
        )

        # Map Prompts to Sessions (Default: 1:1 / Round Robin)
        created_jobs = []
        session_count = len(sessions)

        for idx, p in enumerate(prompts):
            job_number = f"WaqasAutomation_{batch_id}_{idx+1:03d}"
            
            if assignment_mode == "one_to_one":
                s = sessions[idx % session_count]
            else: # round_robin
                s = sessions[idx % session_count]

            db.add_job(
                job_id=job_number,
                batch_id=batch_id,
                prompt_id=p["id"],
                session_id=s["id"]
            )
            created_jobs.append({
                "job_id": job_number,
                "prompt_id": p["id"],
                "session_id": s["id"],
                "prompt_text": p["prompt_text"],
                "session_name": s["name"]
            })

        logger.info(f"Created new batch '{clean_name}' (ID: {batch_id}) with {len(created_jobs)} jobs. Output: {resolved_output_str}", category="BATCH")
        return batch_id, resolved_output_str, created_jobs

    @staticmethod
    def get_batch_history() -> List[Dict[str, Any]]:
        """Returns all historical batches with completion progress statistics."""
        batches = db.get_all_batches()
        history = []
        for b in batches:
            b_dict = dict(b)
            jobs = db.get_batch_jobs(b["id"])
            b_dict["total_jobs"] = len(jobs)
            b_dict["completed_jobs"] = sum(1 for j in jobs if j["status"] == "Completed")
            b_dict["failed_jobs"] = sum(1 for j in jobs if j["status"] == "Failed")
            b_dict["pending_jobs"] = sum(1 for j in jobs if j["status"] in ("Pending", "Starting"))
            history.append(b_dict)
        return history
