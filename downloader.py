"""Core download functionality for YouTube Music Downloader."""

import logging
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Callable

import yt_dlp

from models import DownloadItem, DownloadStatus, AudioFormat, AudioMetadata
from utils import format_bytes, get_file_size, sanitize_filename, get_file_extension

logger = logging.getLogger(__name__)


class YoutubeMusicDownloader:
    """Handles downloading and converting YouTube music."""

    def __init__(
        self,
        output_dir: Path,
        ffmpeg_path: Optional[Path] = None,
        audio_quality: str = "192",
    ):
        """Initialize downloader.

        Args:
            output_dir: Output directory for downloads
            ffmpeg_path: Path to FFmpeg executable
            audio_quality: Audio quality in kbps
        """
        self.output_dir = output_dir
        self.ffmpeg_path = ffmpeg_path
        self.audio_quality = audio_quality
        self.temp_dir = Path(tempfile.gettempdir()) / "youtube_music_downloader"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def download(
        self,
        download_item: DownloadItem,
        progress_callback: Optional[Callable[[float, str, str], None]] = None,
    ) -> bool:
        """Download and convert audio from YouTube URL.

        Args:
            download_item: Download item with URL and format
            progress_callback: Optional callback for progress updates

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Starting download: {download_item.title}")
            download_item.status = DownloadStatus.DOWNLOADING
            download_item.started_at = datetime.now().isoformat()

            info = self._extract_audio(download_item, progress_callback)
            if not info:
                download_item.status = DownloadStatus.FAILED
                download_item.error_message = "Failed to extract audio from URL"
                logger.error(download_item.error_message)
                return False

            download_item.status = DownloadStatus.CONVERTING
            if progress_callback:
                progress_callback(50.0, "0 B/s", "00:00:00")

            success = self._convert_audio(download_item, info)

            if success:
                download_item.status = DownloadStatus.COMPLETED
                download_item.completed_at = datetime.now().isoformat()
                download_item.file_size = get_file_size(Path(download_item.file_path))
                logger.info(f"Download completed: {download_item.title}")
                if progress_callback:
                    progress_callback(100.0, "0 B/s", "00:00:00")
                return True
            else:
                download_item.status = DownloadStatus.FAILED
                download_item.error_message = "Failed to convert audio"
                logger.error(download_item.error_message)
                return False

        except Exception as e:
            logger.error(f"Download error for {download_item.title}: {e}")
            download_item.status = DownloadStatus.FAILED
            download_item.error_message = str(e)
            return False

    def _extract_audio(
        self,
        download_item: DownloadItem,
        progress_callback: Optional[Callable[[float, str, str], None]] = None,
    ) -> Optional[Dict]:
        """Extract audio information and download.

        Args:
            download_item: Download item
            progress_callback: Optional progress callback

        Returns:
            Info dictionary or None on failure
        """
        try:
            ydl_opts = {
                "format": "bestaudio/best",
                "quiet": False,
                "no_warnings": False,
                "extract_flat": False,
                "socket_timeout": 30,
                "outtmpl": str(self.temp_dir / "%(id)s.%(ext)s"),
                "progress_hooks": [
                    lambda d: self._progress_hook(d, progress_callback)
                ],
            }

            if self.ffmpeg_path and self.ffmpeg_path.exists():
                ydl_opts["ffmpeg_location"] = str(self.ffmpeg_path.parent)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(download_item.url, download=True)

                if info:
                    download_item.metadata = AudioMetadata(
                        title=info.get("title", "Unknown"),
                        artist=info.get("uploader", "Unknown"),
                        duration=info.get("duration", 0),
                        thumbnail_url=info.get("thumbnail"),
                        upload_date=info.get("upload_date"),
                    )
                    logger.debug(f"Extracted info: {info.get('title')}")
                    return info

            return None

        except Exception as e:
            logger.error(f"Error extracting audio: {e}")
            return None

    def _progress_hook(
        self,
        d: Dict,
        callback: Optional[Callable[[float, str, str], None]] = None,
    ) -> None:
        """Handle download progress updates.

        Args:
            d: Progress dictionary from yt-dlp
            callback: Optional callback for progress
        """
        try:
            if d["status"] == "downloading":
                total = d.get("total_bytes", 1)
                downloaded = d.get("downloaded_bytes", 0)
                speed = d.get("speed", 0)
                eta = d.get("eta", 0)

                if total > 0:
                    progress = (downloaded / total) * 100
                else:
                    progress = 0

                if callback:
                    from utils import format_speed, format_time

                    callback(progress, format_speed(speed or 0), format_time(int(eta or 0)))

            elif d["status"] == "finished":
                logger.debug("Download finished")
        except Exception as e:
            logger.warning(f"Progress hook error: {e}")

    def _convert_audio(self, download_item: DownloadItem, info: Dict) -> bool:
        """Convert downloaded audio to target format.

        Args:
            download_item: Download item with target format
            info: Info dictionary from yt-dlp

        Returns:
            True if successful, False otherwise
        """
        try:
            video_id = info.get("id")
            if not video_id:
                logger.error("No video ID found")
                return False

            input_file = self.temp_dir / f"{video_id}.webm"
            if not input_file.exists():
                input_file = self.temp_dir / f"{video_id}.m4a"
            if not input_file.exists():
                input_file = self.temp_dir / f"{video_id}.mp3"

            if not input_file.exists():
                possible_files = list(self.temp_dir.glob(f"{video_id}.*"))
                if not possible_files:
                    logger.error(f"No audio file found for video {video_id}")
                    return False
                input_file = possible_files[0]

            if not input_file.exists():
                logger.error(f"Input file not found: {input_file}")
                return False

            title = sanitize_filename(
                download_item.metadata.title
                if download_item.metadata
                else download_item.title
            )
            output_filename = f"{title}{get_file_extension(download_item.audio_format.value)}"
            output_path = self.output_dir / output_filename

            self.output_dir.mkdir(parents=True, exist_ok=True)

            if not self._convert_with_ffmpeg(
                input_file,
                output_path,
                download_item.audio_format,
            ):
                logger.error(f"FFmpeg conversion failed")
                return False

            try:
                input_file.unlink()
            except Exception as e:
                logger.warning(f"Could not delete temp file {input_file}: {e}")

            download_item.file_path = str(output_path)
            logger.info(f"Conversion completed: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error during audio conversion: {e}")
            return False

    def _convert_with_ffmpeg(
        self,
        input_file: Path,
        output_file: Path,
        audio_format: AudioFormat,
    ) -> bool:
        """Convert audio using FFmpeg.

        Args:
            input_file: Input audio file
            output_file: Output audio file
            audio_format: Target audio format

        Returns:
            True if successful, False otherwise
        """
        try:
            ffmpeg_cmd = self._build_ffmpeg_command(
                input_file,
                output_file,
                audio_format,
            )

            logger.debug(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")

            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                return False

            if not output_file.exists():
                logger.error(f"Output file not created: {output_file}")
                return False

            logger.info(f"Audio converted successfully: {output_file}")
            return True

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg conversion timeout")
            return False
        except Exception as e:
            logger.error(f"FFmpeg conversion error: {e}")
            return False

    def _build_ffmpeg_command(
        self,
        input_file: Path,
        output_file: Path,
        audio_format: AudioFormat,
    ) -> list:
        """Build FFmpeg command based on target format.

        Args:
            input_file: Input file path
            output_file: Output file path
            audio_format: Target audio format

        Returns:
            FFmpeg command as list
        """
        ffmpeg_exe = "ffmpeg"
        if self.ffmpeg_path and self.ffmpeg_path.exists():
            ffmpeg_exe = str(self.ffmpeg_path)

        base_cmd = [ffmpeg_exe, "-i", str(input_file), "-vn", "-acodec"]

        format_configs = {
            AudioFormat.MP3: ("libmp3lame", ["-ab", f"{self.audio_quality}k"]),
            AudioFormat.M4A: ("aac", ["-ab", f"{self.audio_quality}k"]),
            AudioFormat.WAV: ("pcm_s16le", []),
            AudioFormat.OPUS: ("libopus", ["-ab", f"{self.audio_quality}k"]),
            AudioFormat.VORBIS: ("libvorbis", ["-ab", f"{self.audio_quality}k"]),
        }

        codec, extra_args = format_configs.get(
            audio_format,
            ("libmp3lame", ["-ab", f"{self.audio_quality}k"]),
        )

        cmd = base_cmd + [codec] + extra_args + ["-y", str(output_file)]

        return cmd

    def cancel_download(self) -> None:
        """Cancel current download."""
        logger.info("Download cancelled")

    def get_info(self, url: str) -> Optional[Dict]:
        """Get information about a YouTube video/audio.

        Args:
            url: YouTube URL

        Returns:
            Info dictionary or None
        """
        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info

        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return None
