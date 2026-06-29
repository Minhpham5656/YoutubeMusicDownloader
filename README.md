# YouTube Music Downloader

A modern, feature-rich YouTube Music Downloader GUI application built with Python 3.14 and PySide6.

## Features

- 🎵 Download and convert audio from YouTube Music content
- ⚡ Multi-threaded downloads without UI freezing
- 📊 Queue management with simultaneous downloads
- 🎨 Modern dark interface theme
- 💾 Automatic settings persistence
- 📝 Comprehensive logging system
- 🛡️ Robust exception handling
- ⚙️ Configurable FFmpeg integration
- 🎯 Production-quality architecture

## Requirements

- Python 3.14+
- Windows OS
- FFmpeg (or bundled executable)
- yt-dlp
- PySide6

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Minhpham5656/YoutubeMusicDownloader.git
cd YoutubeMusicDownloader
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

## Project Structure

```
YoutubeMusicDownloader/
├── main.py                 # Application entry point
├── gui.py                  # Main GUI window
├── widgets.py              # Custom widgets
├── worker.py               # Download worker thread
├── downloader.py           # Core download logic
├── settings.py             # Settings management
├── models.py               # Data models
├── utils.py                # Utility functions
├── config.json             # Configuration file
├── requirements.txt        # Dependencies
├── README.md               # This file
├── assets/                 # UI assets and resources
├── downloads/              # Downloaded files
└── logs/                   # Application logs
```

## License

MIT License
