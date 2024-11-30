# Bunkr Downloader

> A Python-based Bunkr downloader that uses Playwright for browser automation to fetch images and videos from specified URLs, only falling back to Playwright if the main download logic fails. It supports downloading from both Bunkr albums and individual file URLs, while logging any issues. The code also supports multiple concurrent downloads for improved efficiency.

![Screenshot](https://github.com/Lysagxra/SimpleBunkrDownloader/blob/b334cf27fff8ca734b942e32186338592405a45f/misc/Demo.gif)

## Features

- Downloads multiple files from an album concurrently.
- Supports batch downloading via a list of URLs.
- Progress indication during downloads.
- Automatically creates a directory structure for organized storage.
- Logs URLs that encounter errors for troubleshooting.

## Dependencies

- Python 3
- `playwright` - for browser automation and downloading content.
- `BeautifulSoup` (bs4) - for HTML parsing
- `requests` - for HTTP requests
- `rich` - for progress display in the terminal.

## Directory Structure

```
project-root/
├── helpers/
│ ├── managers/
│ │ ├── live_manager.py         # Manages a real-time live display
│ │ ├── log_manager.py          # Manages real-time log updates
│ │ └── progress_manager.py     # Manages progress bars
│ ├── bunkr_utils.py            # Utilities for checking Bunkr status and URL validation
│ ├── download_utils.py         # Utilities for managing the download process
│ ├── file_utils.py             # Utilities for managing file operations
│ ├── general_utils.py          # Miscellaneous utility functions
│ ├── playwright_downloader.py  # Module that utilizes Playwright to automate downloads from Bunkr
│ └── url_utils.py              # Utilities for Bunkr URLs
├── downloader.py               # Module for initiating downloads from specified Bunkr URLs
├── main.py                     # Main script to run the downloader
├── URLs.txt                    # Text file listing album URLs to be downloaded
└── session_log.txt             # Log file for recording session details
```

## Installation

1. Clone the repository:

```bash
git clone https://github.com/Lysagxra/BunkrDownloader.git
```

2. Navigate to the project directory:

```bash
cd BunkrDownloader
```

3. Install the required dependencies:

```bash
pip install -r requirements.txt
```

4. Ensure you have Playwright installed and set up installing Firefox:

```bash
playwright install firefox
```

## Single Media Download

To download a single media from an URL, you can use `downloader.py`, running the script with a valid album or media URL.

### Usage

```bash
python3 downloader.py <bunkr_url>
```

### Example

```
python3 downloader.py https://bunkr.si/a/PUK068QE
```

## Batch Download

To batch download from multiple URLs, you can use the `main.py` script. This script reads URLs from a file named `URLs.txt` and downloads each one using the media downloader.

### Usage

1. Create a file named `URLs.txt` in the root of your project, listing each URL on a new line.

2. Run the batch download script:

```
python3 main.py
```

3. The downloaded files will be saved in the `Downloads` directory.

## Logging

The application logs any issues encountered during the download process in a file named `session_log.txt`. Check this file for any URLs that may have been blocked or had errors.
