"""Settings management for the YouTube Music Downloader application."""

import json
import logging
from pathlib import Path
from typing import Optional

from models import ApplicationSettings, AudioFormat

logger = logging.getLogger(__name__)

CONFIG_FILE = Path("config.json")
DEFAULT_SETTINGS_FILE = Path("user_settings.json")


class SettingsManager:
    """Manages application settings and preferences."""

    def __init__(self, config_path: Path = CONFIG_FILE, settings_path: Path = DEFAULT_SETTINGS_FILE):
        """Initialize settings manager.

        Args:
            config_path: Path to configuration file
            settings_path: Path to user settings file
        """
        self.config_path = config_path
        self.settings_path = settings_path
        self.settings: Optional[ApplicationSettings] = None
        self._load_settings()

    def _load_settings(self) -> None:
        """Load settings from files."""
        try:
            if self.settings_path.exists():
                self._load_from_file(self.settings_path)
                logger.info(f"Settings loaded from: {self.settings_path}")
            elif self.config_path.exists():
                self._load_from_file(self.config_path)
                logger.info(f"Settings loaded from: {self.config_path}")
            else:
                self._create_default_settings()
                logger.info("Default settings created")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            self._create_default_settings()

    def _load_from_file(self, file_path: Path) -> None:
        """Load settings from file.

        Args:
            file_path: Path to settings file
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.settings = ApplicationSettings.from_dict(data)

    def _create_default_settings(self) -> None:
        """Create default settings."""
        self.settings = ApplicationSettings(
            download_directory=Path("./downloads"),
            logs_directory=Path("./logs"),
            ffmpeg_path=Path("./ffmpeg/bin/ffmpeg.exe"),
        )

    def save_settings(self) -> None:
        """Save current settings to file."""
        try:
            if self.settings is None:
                logger.warning("No settings to save")
                return

            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self.settings.to_dict(), f, indent=2)
                logger.debug(f"Settings saved to: {self.settings_path}")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            raise

    def get_settings(self) -> ApplicationSettings:
        """Get current settings.

        Returns:
            ApplicationSettings object
        """
        if self.settings is None:
            self._create_default_settings()

        return self.settings

    def update_setting(self, key: str, value) -> None:
        """Update a single setting.

        Args:
            key: Setting key
            value: New value
        """
        try:
            if self.settings is None:
                self._create_default_settings()

            if hasattr(self.settings, key):
                if key in ("download_directory", "logs_directory", "ffmpeg_path"):
                    value = Path(value) if not isinstance(value, Path) else value

                setattr(self.settings, key, value)
                self.save_settings()
                logger.debug(f"Setting updated: {key} = {value}")
            else:
                logger.warning(f"Unknown setting: {key}")
        except Exception as e:
            logger.error(f"Error updating setting {key}: {e}")
            raise

    def get_setting(self, key: str):
        """Get specific setting value.

        Args:
            key: Setting key

        Returns:
            Setting value or None if not found
        """
        if self.settings is None:
            self._create_default_settings()

        return getattr(self.settings, key, None)

    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        try:
            self._create_default_settings()
            self.save_settings()
            logger.info("Settings reset to defaults")
        except Exception as e:
            logger.error(f"Error resetting settings: {e}")
            raise

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        try:
            if self.settings is None:
                self._create_default_settings()

            self.settings.download_directory.mkdir(parents=True, exist_ok=True)
            self.settings.logs_directory.mkdir(parents=True, exist_ok=True)
            if self.settings.ffmpeg_path.parent.exists():
                self.settings.ffmpeg_path.parent.mkdir(parents=True, exist_ok=True)

            logger.debug("Required directories ensured")
        except Exception as e:
            logger.error(f"Error ensuring directories: {e}")
            raise

    def get_download_directory(self) -> Path:
        """Get download directory."""
        if self.settings is None:
            self._create_default_settings()

        return self.settings.download_directory

    def set_download_directory(self, directory: Path) -> None:
        """Set download directory.

        Args:
            directory: New download directory
        """
        self.update_setting("download_directory", directory)

    def get_max_concurrent_downloads(self) -> int:
        """Get maximum concurrent downloads."""
        if self.settings is None:
            self._create_default_settings()

        return self.settings.max_concurrent_downloads

    def set_max_concurrent_downloads(self, count: int) -> None:
        """Set maximum concurrent downloads.

        Args:
            count: Maximum concurrent download count
        """
        if count < 1 or count > 10:
            logger.warning(f"Invalid concurrent downloads count: {count}")
            return

        self.update_setting("max_concurrent_downloads", count)

    def get_audio_quality(self) -> str:
        """Get audio quality setting."""
        if self.settings is None:
            self._create_default_settings()

        return self.settings.audio_quality

    def set_audio_quality(self, quality: str) -> None:
        """Set audio quality.

        Args:
            quality: Audio quality (e.g., '128', '192', '320')
        """
        self.update_setting("audio_quality", quality)

    def get_default_format(self) -> AudioFormat:
        """Get default audio format."""
        if self.settings is None:
            self._create_default_settings()

        return self.settings.default_format

    def set_default_format(self, format_type: str) -> None:
        """Set default audio format.

        Args:
            format_type: Format type (mp3, m4a, wav, etc.)
        """
        try:
            audio_format = AudioFormat(format_type)
            self.update_setting("default_format", audio_format)
        except ValueError:
            logger.warning(f"Invalid audio format: {format_type}")

    def get_ffmpeg_path(self) -> Path:
        """Get FFmpeg path."""
        if self.settings is None:
            self._create_default_settings()

        return self.settings.ffmpeg_path

    def set_ffmpeg_path(self, path: Path) -> None:
        """Set FFmpeg path.

        Args:
            path: Path to FFmpeg executable
        """
        self.update_setting("ffmpeg_path", path)

    def get_theme(self) -> str:
        """Get current theme."""
        if self.settings is None:
            self._create_default_settings()

        return self.settings.theme

    def set_theme(self, theme: str) -> None:
        """Set theme.

        Args:
            theme: Theme name (dark, light, etc.)
        """
        self.update_setting("theme", theme)

    def is_notification_enabled(self) -> bool:
        """Check if notifications are enabled."""
        if self.settings is None:
            self._create_default_settings()

        return self.settings.notification_enabled

    def set_notification_enabled(self, enabled: bool) -> None:
        """Set notification setting.

        Args:
            enabled: Enable or disable notifications
        """
        self.update_setting("notification_enabled", enabled)

    def is_auto_delete_temp_enabled(self) -> bool:
        """Check if auto delete temp is enabled."""
        if self.settings is None:
            self._create_default_settings()

        return self.settings.auto_delete_temp

    def set_auto_delete_temp_enabled(self, enabled: bool) -> None:
        """Set auto delete temp setting.

        Args:
            enabled: Enable or disable auto delete
        """
        self.update_setting("auto_delete_temp", enabled)
