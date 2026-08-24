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
    HEADER_NAMES = {"prompt", "prompts", "prompt_text", "prompt text", "prompt description", "text", "description", "content", "title"}

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
        with open(path, "rb") as f:
            return PromptManager.import_from_bytes(f.read(), path.name)

    @staticmethod
    def import_from_bytes(file_bytes: bytes, filename: str) -> List[str]:
        """Import prompt strings directly from file bytes (TXT, CSV, XLSX, XLS)."""
        if not file_bytes:
            return []

        ext = Path(filename).suffix.lower()
        prompts: List[str] = []

        if ext == ".txt":
            for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
                try:
                    text = file_bytes.decode(enc)
                    prompts = PromptManager.parse_text_lines(text)
                    break
                except UnicodeDecodeError:
                    continue

        elif ext == ".csv":
            import io
            for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
                try:
                    text = file_bytes.decode(enc)
                    reader = csv.reader(io.StringIO(text))
                    for idx, row in enumerate(reader):
                        if row and str(row[0]).strip():
                            val = str(row[0]).strip()
                            if idx == 0 and val.lower() in PromptManager.HEADER_NAMES:
                                continue
                            prompts.append(val)
                    break
                except UnicodeDecodeError:
                    continue

        elif ext in (".xlsx", ".xlsm", ".xltx", ".xltm", ".xls"):
            import io
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
            sheet = wb.active
            for idx, row in enumerate(sheet.iter_rows(values_only=True)):
                if row and row[0] is not None:
                    val = str(row[0]).strip()
                    if val:
                        if idx == 0 and val.lower() in PromptManager.HEADER_NAMES:
                            continue
                        prompts.append(val)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Supported formats: .txt, .csv, .xlsx, .xls")

        return prompts

    @staticmethod
    def save_prompts(prompt_list: List[str], ratio: str = "9:16", duration: int = 10, model: str = "Seedance 2.0", category: str = "General", deduct_duplicates: bool = True) -> Tuple[int, int]:
        """
        Saves a list of prompt strings to database using high-speed bulk insertion.
        Returns tuple of (added_count, duplicate_count).
        """
        if not prompt_list:
            return 0, 0

        existing = set()
        if deduct_duplicates:
            existing = {p["prompt_text"].lower().strip() for p in db.get_all_prompts()}

        to_add = []
        duplicates = 0

        for p_text in prompt_list:
            clean_text = p_text.strip()
            if not clean_text:
                continue

            if deduct_duplicates and clean_text.lower() in existing:
                duplicates += 1
                continue

            to_add.append((clean_text, category, ratio, duration, model))
            if deduct_duplicates:
                existing.add(clean_text.lower())

        if to_add:
            db.add_prompts_bulk(to_add, category=category)

        added = len(to_add)
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
        """Deletes multiple prompts from database by ID list in a single bulk transaction."""
        if not prompt_ids:
            return
        db.delete_prompts_bulk(prompt_ids)
        logger.info(f"Deleted {len(prompt_ids)} selected prompts from database.", category="PROMPTS")
