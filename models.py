"""Data models for the YouTube Music Downloader application."""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


class DownloadStatus(Enum):
    """Enumeration of download statuses."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    CONVERTING = "converting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class AudioFormat(Enum):
    """Supported audio formats."""

    MP3 = "mp3"
    M4A = "m4a"
    WAV = "wav"
    OPUS = "opus"
    VORBIS = "vorbis"


@dataclass
class AudioMetadata:
    """Audio metadata information."""

    title: str
    artist: str
    album: Optional[str] = None
    duration: int = 0
    thumbnail_url: Optional[str] = None
    upload_date: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AudioMetadata":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class DownloadItem:
    """Represents a single download item in the queue."""

    url: str
    title: str
    audio_format: AudioFormat
    status: DownloadStatus = DownloadStatus.PENDING
    progress: float = 0.0
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Optional[AudioMetadata] = None
    file_size: int = 0
    speed: str = "0 B/s"
    eta: str = "00:00:00"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        data["audio_format"] = self.audio_format.value
        if self.metadata:
            data["metadata"] = self.metadata.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "DownloadItem":
        """Create from dictionary."""
        data = data.copy()
        data["status"] = DownloadStatus(data.get("status", "pending"))
        data["audio_format"] = AudioFormat(data.get("audio_format", "mp3"))
        if data.get("metadata"):
            data["metadata"] = AudioMetadata.from_dict(data["metadata"])
        return cls(**data)

    def get_status_display(self) -> str:
        """Get human-readable status display."""
        if self.status == DownloadStatus.DOWNLOADING:
            return f"Downloading ({self.progress:.1f}%)"
        elif self.status == DownloadStatus.CONVERTING:
            return "Converting..."
        return self.status.value.capitalize()

    def is_active(self) -> bool:
        """Check if download is currently active."""
        return self.status in (DownloadStatus.DOWNLOADING, DownloadStatus.CONVERTING)


@dataclass
class ApplicationSettings:
    """Application settings and preferences."""

    download_directory: Path
    logs_directory: Path
    ffmpeg_path: Path
    max_concurrent_downloads: int = 3
    chunk_size: int = 8192
    timeout: int = 30
    theme: str = "dark"
    default_format: AudioFormat = AudioFormat.MP3
    audio_quality: str = "192"
    remember_last_directory: bool = True
    auto_delete_temp: bool = True
    notification_enabled: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "download_directory": str(self.download_directory),
            "logs_directory": str(self.logs_directory),
            "ffmpeg_path": str(self.ffmpeg_path),
            "max_concurrent_downloads": self.max_concurrent_downloads,
            "chunk_size": self.chunk_size,
            "timeout": self.timeout,
            "theme": self.theme,
            "default_format": self.default_format.value,
            "audio_quality": self.audio_quality,
            "remember_last_directory": self.remember_last_directory,
            "auto_delete_temp": self.auto_delete_temp,
            "notification_enabled": self.notification_enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ApplicationSettings":
        """Create from dictionary."""
        return cls(
            download_directory=Path(data.get("download_directory", "./downloads")),
            logs_directory=Path(data.get("logs_directory", "./logs")),
            ffmpeg_path=Path(data.get("ffmpeg_path", "./ffmpeg/bin/ffmpeg.exe")),
            max_concurrent_downloads=data.get("max_concurrent_downloads", 3),
            chunk_size=data.get("chunk_size", 8192),
            timeout=data.get("timeout", 30),
            theme=data.get("theme", "dark"),
            default_format=AudioFormat(data.get("default_format", "mp3")),
            audio_quality=data.get("audio_quality", "192"),
            remember_last_directory=data.get("remember_last_directory", True),
            auto_delete_temp=data.get("auto_delete_temp", True),
            notification_enabled=data.get("notification_enabled", True),
        )


@dataclass
class DownloadStats:
    """Statistics for downloads."""

    total_downloads: int = 0
    completed_downloads: int = 0
    failed_downloads: int = 0
    total_data_downloaded: int = 0
    average_speed: str = "0 B/s"
    total_time: str = "00:00:00"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DownloadStats":
        """Create from dictionary."""
        return cls(**data)


class DownloadQueue:
    """Manages the download queue."""

    def __init__(self) -> None:
        """Initialize the download queue."""
        self.items: List[DownloadItem] = []
        self.history: List[DownloadItem] = []

    def add_item(self, item: DownloadItem) -> None:
        """Add item to queue."""
        self.items.append(item)
        logger.debug(f"Added item to queue: {item.title}")

    def remove_item(self, url: str) -> Optional[DownloadItem]:
        """Remove item from queue by URL."""
        for i, item in enumerate(self.items):
            if item.url == url:
                removed = self.items.pop(i)
                logger.debug(f"Removed item from queue: {removed.title}")
                return removed
        return None

    def get_item(self, url: str) -> Optional[DownloadItem]:
        """Get item from queue by URL."""
        for item in self.items:
            if item.url == url:
                return item
        return None

    def clear_queue(self) -> None:
        """Clear the queue."""
        self.items.clear()
        logger.debug("Queue cleared")

    def get_pending_items(self) -> List[DownloadItem]:
        """Get all pending items."""
        return [item for item in self.items if item.status == DownloadStatus.PENDING]

    def get_active_items(self) -> List[DownloadItem]:
        """Get all active downloads."""
        return [item for item in self.items if item.is_active()]

    def get_failed_items(self) -> List[DownloadItem]:
        """Get all failed items."""
        return [item for item in self.items if item.status == DownloadStatus.FAILED]

    def move_to_history(self, item: DownloadItem) -> None:
        """Move completed item to history."""
        if item in self.items:
            self.items.remove(item)
            self.history.append(item)
            logger.debug(f"Moved item to history: {item.title}")

    def get_queue_size(self) -> int:
        """Get current queue size."""
        return len(self.items)

    def get_active_count(self) -> int:
        """Get count of active downloads."""
        return len(self.get_active_items())

    def to_dict(self) -> dict:
        """Convert queue to dictionary."""
        return {
            "items": [item.to_dict() for item in self.items],
            "history": [item.to_dict() for item in self.history],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DownloadQueue":
        """Create from dictionary."""
        queue = cls()
        for item_data in data.get("items", []):
            queue.items.append(DownloadItem.from_dict(item_data))
        for item_data in data.get("history", []):
            queue.history.append(DownloadItem.from_dict(item_data))
        return queue
