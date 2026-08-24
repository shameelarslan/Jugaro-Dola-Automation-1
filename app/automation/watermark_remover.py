"""
Watermark Remover Engine using built-in FFmpeg.
Applies localized high-speed bounding box blur filter on specified coordinates (X, Y, W, H).
Preserves original audio, frame rates, and visual fidelity.
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional
import imageio_ffmpeg
from app.core.logger import logger

class WatermarkRemover:
    @staticmethod
    def get_ffmpeg_path() -> str:
        """Returns the absolute path to the bundled FFmpeg executable."""
        try:
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return "ffmpeg"

    @classmethod
    def remove_watermark(
        cls,
        input_mp4: str,
        output_mp4: str,
        x: int = 540,
        y: int = 1220,
        w: int = 170,
        h: int = 50,
        blur_size: int = 20
    ) -> bool:
        """
        Removes/blurs watermark at (x, y, w, h) from input_mp4 and saves to output_mp4.
        Returns True on success, False on failure.
        """
        if not os.path.exists(input_mp4):
            logger.error(f"Watermark remover: Input file not found: {input_mp4}", category="WATERMARK")
            return False

        ffmpeg_bin = cls.get_ffmpeg_path()
        if not ffmpeg_bin:
            logger.error("Watermark remover: FFmpeg binary not available", category="WATERMARK")
            return False

        temp_out = f"{output_mp4}.wm_temp_{os.getpid()}.mp4"
        try:
            # Build localized blur overlay filter
            filter_str = f"[0:v]crop={w}:{h}:{x}:{y},avgblur=sizeX={blur_size}:sizeY={blur_size}[b];[0:v][b]overlay={x}:{y}"

            cmd = [
                ffmpeg_bin,
                "-y",
                "-i", str(input_mp4),
                "-filter_complex", filter_str,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "18",
                "-c:a", "copy",
                temp_out
            ]

            logger.info(f"🧼 Removing watermark with Blur method (X={x}, Y={y}, W={w}, H={h})...", category="WATERMARK")
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)

            if proc.returncode == 0 and os.path.exists(temp_out) and os.path.getsize(temp_out) > 500:
                os.makedirs(os.path.dirname(output_mp4), exist_ok=True)
                if os.path.exists(output_mp4):
                    try:
                        os.remove(output_mp4)
                    except Exception:
                        pass
                shutil.move(temp_out, output_mp4)
                logger.info(f"✅ Watermark successfully blurred & saved to: {output_mp4}", category="WATERMARK")
                return True
            else:
                logger.warning(f"Watermark remover notice (returncode {proc.returncode}): {proc.stderr[:200]}", category="WATERMARK")
                if os.path.exists(temp_out):
                    try:
                        os.remove(temp_out)
                    except Exception:
                        pass
                return False

        except Exception as e:
            logger.error(f"Watermark removal error: {e}", category="WATERMARK")
            if os.path.exists(temp_out):
                try:
                    os.remove(temp_out)
                except Exception:
                    pass
            return False
