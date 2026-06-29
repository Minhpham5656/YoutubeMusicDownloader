"""Utility functions for the YouTube Music Downloader application."""

import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def setup_logging(log_dir: Path) -> None:
    """Setup logging configuration.

    Args:
        log_dir: Directory for log files
    """
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"youtube_music_downloader_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logger.info(f"Logging initialized. Log file: {log_file}")


def format_bytes(bytes_value: int) -> str:
    """Format bytes to human-readable format.

    Args:
        bytes_value: Number of bytes

    Returns:
        Human-readable string
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def format_speed(bytes_per_second: float) -> str:
    """Format download speed to human-readable format.

    Args:
        bytes_per_second: Bytes per second

    Returns:
        Human-readable speed string
    """
    return f"{format_bytes(int(bytes_per_second))}/s"


def format_time(seconds: int) -> str:
    """Format seconds to HH:MM:SS format.

    Args:
        seconds: Number of seconds

    Returns:
        Formatted time string
    """
    if seconds < 0:
        return "00:00:00"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def calculate_eta(total_bytes: int, downloaded_bytes: int, speed: float) -> str:
    """Calculate estimated time remaining.

    Args:
        total_bytes: Total file size
        downloaded_bytes: Already downloaded bytes
        speed: Download speed in bytes/second

    Returns:
        Formatted ETA string
    """
    if speed <= 0 or downloaded_bytes >= total_bytes:
        return "00:00:00"

    remaining_bytes = total_bytes - downloaded_bytes
    eta_seconds = int(remaining_bytes / speed)

    return format_time(eta_seconds)


def is_valid_url(url: str) -> bool:
    """Validate if string is a valid URL.

    Args:
        url: URL string to validate

    Returns:
        True if valid URL, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def is_youtube_url(url: str) -> bool:
    """Check if URL is from YouTube.

    Args:
        url: URL to check

    Returns:
        True if YouTube URL, False otherwise
    """
    if not is_valid_url(url):
        return False

    youtube_domains = [
        "youtube.com",
        "youtu.be",
        "music.youtube.com",
    ]

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        return any(youtube_domain in domain for youtube_domain in youtube_domains)
    except Exception:
        logger.warning(f"Error validating YouTube URL: {url}")
        return False


def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from YouTube URL.

    Args:
        url: YouTube URL

    Returns:
        Video ID or None if not found
    """
    try:
        parsed = urlparse(url)

        if "youtu.be" in parsed.netloc:
            return parsed.path.lstrip("/")

        if "youtube.com" in parsed.netloc:
            query_params = parsed.query.split("&")
            for param in query_params:
                if param.startswith("v="):
                    return param.split("=", 1)[1]

        return None
    except Exception as e:
        logger.warning(f"Error extracting video ID: {e}")
        return None


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    invalid_chars = r'<>:"/\|?*'

    for char in invalid_chars:
        filename = filename.replace(char, "_")

    filename = filename.strip(". ")

    return filename


def get_file_extension(format_type: str) -> str:
    """Get file extension for audio format.

    Args:
        format_type: Audio format type

    Returns:
        File extension with dot
    """
    extensions = {
        "mp3": ".mp3",
        "m4a": ".m4a",
        "wav": ".wav",
        "opus": ".opus",
        "vorbis": ".ogg",
    }

    return extensions.get(format_type.lower(), ".mp3")


def ensure_directory(directory: Path) -> None:
    """Ensure directory exists, create if needed.

    Args:
        directory: Directory path
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Directory ensured: {directory}")
    except Exception as e:
        logger.error(f"Error creating directory {directory}: {e}")
        raise


def clean_temp_files(temp_dir: Path, max_age_hours: int = 24) -> None:
    """Clean up old temporary files.

    Args:
        temp_dir: Temporary directory path
        max_age_hours: Maximum age of files to keep in hours
    """
    try:
        if not temp_dir.exists():
            return

        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        for file_path in temp_dir.iterdir():
            if file_path.is_file():
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_mtime < cutoff_time:
                    file_path.unlink()
                    logger.debug(f"Deleted temp file: {file_path}")
    except Exception as e:
        logger.warning(f"Error cleaning temp files: {e}")


def check_ffmpeg_available(ffmpeg_path: Optional[Path] = None) -> bool:
    """Check if FFmpeg is available.

    Args:
        ffmpeg_path: Path to FFmpeg executable

    Returns:
        True if FFmpeg available, False otherwise
    """
    try:
        if ffmpeg_path and ffmpeg_path.exists():
            result = subprocess.run(
                [str(ffmpeg_path), "-version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                logger.info(f"FFmpeg found at: {ffmpeg_path}")
                return True

        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            logger.info("FFmpeg found in system PATH")
            return True

        logger.warning("FFmpeg not found")
        return False
    except Exception as e:
        logger.warning(f"Error checking FFmpeg availability: {e}")
        return False


def get_file_size(file_path: Path) -> int:
    """Get file size in bytes.

    Args:
        file_path: Path to file

    Returns:
        File size in bytes, 0 if file not found
    """
    try:
        if file_path.exists():
            return file_path.stat().st_size
        return 0
    except Exception as e:
        logger.warning(f"Error getting file size: {e}")
        return 0


def move_file(source: Path, destination: Path) -> bool:
    """Move file from source to destination.

    Args:
        source: Source file path
        destination: Destination file path

    Returns:
        True if successful, False otherwise
    """
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        logger.debug(f"File moved: {source} -> {destination}")
        return True
    except Exception as e:
        logger.error(f"Error moving file: {e}")
        return False


def delete_file(file_path: Path) -> bool:
    """Delete file.

    Args:
        file_path: Path to file

    Returns:
        True if successful, False otherwise
    """
    try:
        if file_path.exists():
            file_path.unlink()
            logger.debug(f"File deleted: {file_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        return False


def path_to_string(path: Optional[Path]) -> Optional[str]:
    """Convert Path object to string.

    Args:
        path: Path object

    Returns:
        String path or None
    """
    return str(path) if path else None


def string_to_path(string: Optional[str]) -> Optional[Path]:
    """Convert string to Path object.

    Args:
        string: String path

    Returns:
        Path object or None
    """
    return Path(string) if string else None


def get_system_info() -> dict:
    """Get system information.

    Returns:
        Dictionary with system info
    """
    return {
        "platform": sys.platform,
        "python_version": sys.version,
        "executable": sys.executable,
        "cpu_count": os.cpu_count(),
    }


def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """Truncate string to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix
