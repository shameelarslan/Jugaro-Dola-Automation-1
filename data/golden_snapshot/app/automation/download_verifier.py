"""
Concurrency-Safe Download Verifier for Extension MP4 Downloads.
Monitors download directories, snapshots file baselines, and verifies stable MP4 creation.
Includes direct video URL downloader as fallback when extension download fails.
"""

import os
import time
import asyncio
import urllib.request
from pathlib import Path
from typing import Set, Dict, Any, Optional, Tuple
from app.core.logger import logger

class DownloadVerifier:
    def __init__(
        self,
        download_dir: str,
        timeout_sec: float = 60.0,
        worker_id: Optional[int] = None,
        job_id: Optional[str] = None,
        additional_dirs: Optional[list] = None
    ):
        self.download_dir = download_dir
        self.timeout_sec = timeout_sec
        self.worker_id = worker_id
        self.job_id = job_id
        self.additional_dirs = [str(d) for d in (additional_dirs or []) if d]

    async def verify_download(self) -> Optional[Path]:
        """
        Monitors self.download_dir, additional search directories, and user Downloads for any valid completed video file.
        Waits for file size to stabilize and returns Path(file) or None.
        """
        search_dirs = [Path(self.download_dir)]
        for d in self.additional_dirs:
            p = Path(d)
            if p not in search_dirs:
                search_dirs.append(p)

        for p in search_dirs:
            p.mkdir(parents=True, exist_ok=True)

        start_wait = time.time()

        while time.time() - start_wait < self.timeout_sec:
            candidates = []
            for p in search_dirs:
                if p.exists():
                    try:
                        for f in p.iterdir():
                            if f.is_file() and not f.name.endswith(".crdownload") and not f.name.endswith(".tmp"):
                                try:
                                    if f.stat().st_size > 50_000:
                                        candidates.append(f)
                                except Exception:
                                    pass
                    except Exception:
                        pass



            if candidates:
                candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                target = candidates[0]

                # Wait for file size stabilization
                last_sz = -1
                stable = 0
                for _ in range(10):
                    if target.exists():
                        cur_sz = target.stat().st_size
                        if cur_sz > 50_000 and cur_sz == last_sz:
                            stable += 1
                            if stable >= 2:
                                return target
                        else:
                            stable = 0
                            last_sz = cur_sz
                    await asyncio.sleep(0.5)

                if target.exists() and target.stat().st_size > 50_000:
                    return target

            await asyncio.sleep(1.0)
        return None

    @staticmethod
    async def direct_download_video(
        video_url: str,
        output_folder: str,
        worker_id: Optional[int] = None,
        job_id: Optional[str] = None
    ) -> Optional[Tuple[str, int]]:
        """
        Downloads a video from a direct URL to the output_folder.
        Used as fallback when extension download is not triggered.
        Returns (absolute_filepath, filesize_bytes) or None on failure.
        """
        try:
            output_path = Path(output_folder)
            output_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = int(time.time())
            filename = f"Dola_Video_{timestamp}.mp4"
            dest = output_path / filename
            
            logger.info(f"Direct downloading video to: {dest}", category="DOWNLOAD", worker_id=worker_id, job_id=job_id)
            
            # Run blocking urllib download in executor to keep async event loop free
            loop = asyncio.get_event_loop()
            
            def _download():
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://www.dola.com/",
                }
                req = urllib.request.Request(video_url, headers=headers)
                with urllib.request.urlopen(req, timeout=120) as response:
                    data = response.read()
                with open(dest, "wb") as f:
                    f.write(data)
                return len(data)
            
            file_size = await loop.run_in_executor(None, _download)
            
            if file_size > 0:
                logger.info(f"Direct download complete: {filename} ({file_size / (1024*1024):.2f} MB)", category="DOWNLOAD", worker_id=worker_id, job_id=job_id)
                return str(dest.resolve()), file_size
            else:
                logger.error("Direct download produced empty file.", category="DOWNLOAD", worker_id=worker_id, job_id=job_id)
                return None
                
        except Exception as e:
            logger.error(f"Direct download failed: {e}", category="DOWNLOAD", worker_id=worker_id, job_id=job_id)
            return None

    @staticmethod
    def snapshot_directory(download_dir: str) -> Tuple[Set[str], float]:
        """
        Takes a snapshot of existing files before triggering page reload.
        Tracks both .mp4 files and UUID-named files (extension sometimes saves without .mp4 ext).
        """
        dir_path = Path(download_dir)
        dir_path.mkdir(parents=True, exist_ok=True)

        snapshot_time = time.time()
        existing_files = set()

        for f in dir_path.iterdir():
            existing_files.add(str(f.resolve()))

        # Also snapshot Chrome Downloads
        chrome_dl = Path.home() / "Downloads"
        if chrome_dl.exists():
            for f in chrome_dl.iterdir():
                existing_files.add(str(f.resolve()))

        return existing_files, snapshot_time

    @staticmethod
    async def wait_for_new_download(
        download_dir: str,
        baseline_files: Set[str],
        baseline_time: float,
        timeout_sec: float = 90.0,
        worker_id: Optional[int] = None,
        job_id: Optional[str] = None
    ) -> Optional[Tuple[str, int]]:
        """
        Monitors download_dir AND Chrome's default Downloads folder for a new video file.
        Extension may save as .mp4 OR as a UUID-named file without extension.
        Detection: any new file >100KB that wasn't in baseline snapshot.
        Moves file to output folder with clean Awaiso_Auto_ filename.
        """
        import shutil
        output_path = Path(download_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        chrome_downloads = Path.home() / "Downloads"
        search_dirs = [output_path]
        if chrome_downloads.exists() and chrome_downloads.resolve() != output_path.resolve():
            search_dirs.append(chrome_downloads)

        logger.info(f"Monitoring for video download in: {[str(d) for d in search_dirs]}", category="DOWNLOAD", worker_id=worker_id, job_id=job_id)

        start_wait = time.time()
        target_file: Optional[Path] = None

        while time.time() - start_wait < timeout_sec:
            for search_dir in search_dirs:
                try:
                    for f in search_dir.iterdir():
                        if not f.is_file():
                            continue
                        abs_path = str(f.resolve())
                        if abs_path in baseline_files:
                            continue
                        # Skip .crdownload (still downloading) and tiny files
                        if f.suffix.lower() == ".crdownload":
                            continue
                        try:
                            fsize = f.stat().st_size
                            mtime = f.stat().st_mtime
                        except Exception:
                            continue
                        # Must be >100KB and newer than baseline (5s tolerance)
                        if fsize > 100_000 and mtime >= (baseline_time - 5.0):
                            target_file = f
                            break
                except Exception:
                    pass
                if target_file:
                    break
            if target_file:
                break
            await asyncio.sleep(1.5)

        if not target_file:
            logger.error(f"Download verification timed out after {timeout_sec}s. No new video file found.", category="DOWNLOAD", worker_id=worker_id, job_id=job_id)
            return None

        # Wait for file size to stabilize (download complete)
        logger.info(f"Video file detected: {target_file.name} — waiting for stable size...", category="DOWNLOAD", worker_id=worker_id, job_id=job_id)
        last_size = -1
        stable_checks = 0
        for _ in range(25):
            if target_file.exists():
                curr_size = target_file.stat().st_size
                if curr_size > 0 and curr_size == last_size:
                    stable_checks += 1
                    if stable_checks >= 2:
                        break
                else:
                    stable_checks = 0
                    last_size = curr_size
            await asyncio.sleep(1.0)

        if not target_file.exists() or target_file.stat().st_size == 0:
            return None

        final_size = target_file.stat().st_size

        # Build clean destination filename: Awaiso_Auto_<timestamp>.mp4
        clean_name = f"Awaiso_Auto_{int(time.time() * 1000)}.mp4"
        dest = output_path / clean_name

        # Move (or copy) to output folder with clean name
        try:
            if target_file.resolve() != dest.resolve():
                shutil.move(str(target_file), str(dest))
                logger.info(f"Moved & renamed → {dest.name} ({final_size / (1024*1024):.2f} MB)", category="DOWNLOAD", worker_id=worker_id, job_id=job_id)
                target_file = dest
        except Exception as e:
            logger.warning(f"Could not rename/move file: {e}. Using original path.", category="DOWNLOAD", worker_id=worker_id, job_id=job_id)

        logger.info(f"Verified download: {target_file.name} ({final_size / (1024*1024):.2f} MB)", category="DOWNLOAD", worker_id=worker_id, job_id=job_id)
        return str(target_file.resolve()), final_size

    @staticmethod
    async def is_file_stable(filepath: str, min_size: int = 10000) -> bool:
        """Verifies that a file exists, size > min_size, and size remains stable."""
        try:
            p = Path(filepath)
            if not p.exists():
                return False
            last_size = -1
            stable = 0
            for _ in range(6):
                if not p.exists():
                    return False
                sz = p.stat().st_size
                if sz > min_size and sz == last_size:
                    stable += 1
                    if stable >= 2:
                        return True
                else:
                    stable = 0
                    last_size = sz
                await asyncio.sleep(0.5)
            return p.exists() and p.stat().st_size > min_size
        except Exception:
            return False

    @staticmethod
    async def wait_for_new_file(
        download_dir: str,
        baseline_files: Set[str],
        baseline_time: float,
        timeout_sec: float = 90.0,
        worker_id: Optional[int] = None,
        job_id: Optional[str] = None
    ) -> Optional[str]:
        """Alias method for wait_for_new_download that returns single filepath string or None."""
        res = await DownloadVerifier.wait_for_new_download(download_dir, baseline_files, baseline_time, timeout_sec, worker_id, job_id)
        if res:
            return res[0]
        return None
