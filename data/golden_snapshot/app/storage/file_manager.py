import shutil
from pathlib import Path
from config import INPUT_DIR, ARCHIVE_DIR
from app.utils.logger import log_info, log_error, log_warning

class FileManager:
    """
    Manages video file assets across data/input/{PageName}/ and data/archive/{PageName}/.
    Enforces atomic archiving only after publication verification.
    """
    def __init__(self, input_dir=INPUT_DIR, archive_dir=ARCHIVE_DIR):
        self.input_dir = Path(input_dir)
        self.archive_dir = Path(archive_dir)

    def ensure_page_folders(self, page_name: str):
        """Creates input and archive directories for a specific page."""
        page_input = self.input_dir / page_name
        page_archive = self.archive_dir / page_name
        page_input.mkdir(parents=True, exist_ok=True)
        page_archive.mkdir(parents=True, exist_ok=True)
        return page_input, page_archive

    def get_pending_videos(self, page_name: str):
        """Returns list of pending .mp4 files in data/input/{page_name}/."""
        page_input, _ = self.ensure_page_folders(page_name)
        return [f for f in page_input.glob("*.mp4") if f.is_file()]

    def archive_video(self, video_path: str, page_name: str) -> bool:
        """
        Moves published video file from input to archive directory.
        Must ONLY be called after publication verification SUCCESS.
        """
        src = Path(video_path)
        if not src.exists():
            log_error(f"Cannot archive non-existent file: {video_path}", tag="FILE")
            return False

        _, page_archive = self.ensure_page_folders(page_name)
        dest = page_archive / src.name

        try:
            shutil.move(str(src), str(dest))
            log_info(f"Archived video to: {dest}", tag="FILE")
            return True
        except Exception as e:
            log_error(f"Failed to archive video {src.name}: {str(e)}", tag="FILE")
            return False
