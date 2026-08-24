"""
Prompt Manager Module for Bulk Parsing, TXT/CSV/XLSX Importing, Exporting & Deduplication.
"""

import os
import csv
from typing import List, Dict, Any, Tuple
from pathlib import Path
from app.core.database import db
from app.core.logger import logger

class PromptManager:
    @staticmethod
    def parse_text_lines(text: str) -> List[str]:
        """Parse raw multiline text input into clean non-empty prompt strings."""
        if not text:
            return []
        lines = [line.strip() for line in text.splitlines()]
        return [l for l in lines if l]

    @staticmethod
    def import_from_file(file_path: str) -> List[str]:
        """Import prompt strings from TXT, CSV, or XLSX files."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = path.suffix.lower()
        prompts: List[str] = []

        if ext == ".txt":
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                prompts = PromptManager.parse_text_lines(f.read())
        elif ext == ".csv":
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and row[0].strip():
                        prompts.append(row[0].strip())
        elif ext in (".xlsx", ".xls"):
            import pandas as pd
            df = pd.read_excel(path, header=None)
            if not df.empty:
                first_col = df.iloc[:, 0].dropna()
                prompts = [str(val).strip() for val in first_col if str(val).strip()]
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        return prompts

    @staticmethod
    def save_prompts(prompt_list: List[str], ratio: str = "9:16", duration: int = 10, model: str = "Seedance 2.0", deduct_duplicates: bool = True) -> Tuple[int, int]:
        """
        Saves a list of prompt strings to database.
        Returns tuple of (added_count, duplicate_count).
        """
        existing = {p["prompt_text"].lower().strip() for p in db.get_all_prompts()}
        added = 0
        duplicates = 0

        for p_text in prompt_list:
            clean_text = p_text.strip()
            if not clean_text:
                continue

            if deduct_duplicates and clean_text.lower() in existing:
                duplicates += 1
                continue

            db.add_prompt(clean_text, ratio, duration, model)
            existing.add(clean_text.lower())
            added += 1

        logger.info(f"Imported {added} prompts into database ({duplicates} duplicates skipped).", category="PROMPTS")
        return added, duplicates

    @staticmethod
    def export_prompts(file_path: str, format_type: str = "csv"):
        """Export current prompts from database to file."""
        prompts = db.get_all_prompts()
        path = Path(file_path)

        if format_type.lower() == "txt":
            with open(path, "w", encoding="utf-8") as f:
                for p in prompts:
                    f.write(p["prompt_text"] + "\n")
        elif format_type.lower() == "csv":
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Prompt", "Ratio", "Duration", "Model", "Status"])
                for p in prompts:
                    writer.writerow([p["id"], p["prompt_text"], p["ratio"], p["duration"], p["model"], p["status"]])
        elif format_type.lower() in ("xlsx", "excel"):
            import pandas as pd
            df = pd.DataFrame(prompts)
            df.to_excel(path, index=False)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

    @staticmethod
    def delete_prompt(prompt_id: int):
        """Deletes a single prompt from database by ID."""
        db.delete_prompt(prompt_id)
        logger.info(f"Deleted prompt ID {prompt_id} from database.", category="PROMPTS")

    @staticmethod
    def delete_prompts(prompt_ids: List[int]):
        """Deletes multiple prompts from database by ID list."""
        for p_id in prompt_ids:
            db.delete_prompt(p_id)
        logger.info(f"Deleted {len(prompt_ids)} selected prompts from database.", category="PROMPTS")
