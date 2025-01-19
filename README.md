# Bunkr Downloader

> A Python Bunkr downloader that fetches images and videos from URLs. It supports both Bunkr albums and individual file URLs, logs issues, and enables concurrent downloads for efficiency.

![Screenshot](https://github.com/Lysagxra/BunkrDownloader/blob/3bc786d91f2950fbc1df120b7ebbb6ff90e4e6fd/misc/DemoV2.gif)

## Features

- Downloads multiple files from an album concurrently.
- Supports batch downloading via a list of URLs.
- Skips files whose filenames contain any string in the ignore list, if provided.
- Progress indication during downloads.
- Automatically creates a directory structure for organized storage.
- Logs URLs that encounter errors for troubleshooting.

## Dependencies

- Python 3
- `BeautifulSoup` (bs4) - for HTML parsing
- `requests` - for HTTP requests
- `rich` - for progress display in the terminal.

## Directory Structure

```
project-root/
├── helpers/
│ ├── crawlers/
│ │ └── crawler_utils.py     # Utilities for extracting media download links
│ ├── managers/
│ │ ├── live_manager.py      # Manages a real-time live display
│ │ ├── log_manager.py       # Manages real-time log updates
│ │ └── progress_manager.py  # Manages progress bars
│ ├── bunkr_utils.py         # Utilities for checking Bunkr status
│ ├── config.py              # Manages constants and settings used across the project
│ ├── download_utils.py      # Utilities for managing the download process
│ ├── file_utils.py          # Utilities for managing file operations
│ ├── general_utils.py       # Miscellaneous utility functions
│ └── url_utils.py           # Utilities for Bunkr URLs
├── downloader.py            # Module for initiating downloads from specified Bunkr URLs
├── main.py                  # Main script to run the downloader
├── URLs.txt                 # Text file listing album URLs to be downloaded
└── session_log.txt          # Log file for recording session details
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

## Single Download

To download a single media from an URL, you can use `downloader.py`, running the script with a valid album or media URL.

### Usage

```bash
python3 downloader.py <bunkr_url>
```

### Examples

```
python3 downloader.py https://bunkr.si/a/PUK068QE       # Download album
python3 downloader.py https://bunkr.fi/f/gBrv5f8tAGlGW  # Download single media
```

## Ignore List

The ignore list is specified using the `--ignore` argument in the command line. This allows you to skip the download of any file from an album if its filename contains at least one of the specified strings in the ignore list. Each item in the list should be separated by a space.

### Usage

```bash
python3 downloader.py <bunkr_album_url> --ignore <ignore_list>
```

### Examples

This feature is particularly useful when you want to skip files with certain extensions, such as `.zip` files. For instance:

```bash
python3 downloader.py https://bunkr.si/a/PUK068QE --ignore .zip
```

## Batch Download

To batch download from multiple URLs, you can use the `main.py` script. This script reads URLs from a file named `URLs.txt` and downloads each one using the media downloader.

### Usage

1. Create a file named `URLs.txt` in the root of your project, listing each URL on a new line.

- Example of `URLs.txt`:

```
https://bunkr.si/a/PUK068QE
https://bunkr.fi/f/gBrv5f8tAGlGW
https://bunkr.fi/a/kVYLh49Q
```

- Ensure that each URL is on its own line without any extra spaces.
- You can add as many URLs as you need, following the same format.

2. Run the batch download script:

```
python3 main.py
```

3. The downloaded files will be saved in the `Downloads` directory.

## Logging

The application logs any issues encountered during the download process in a file named `session_log.txt`. Check this file for any URLs that may have been blocked or had errors.
