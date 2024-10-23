# Simple Bunkr Downloader for Linux

A Python-based Bunkr downloader that utilizes Playwright for browser automation to fetch and download images and videos from specified URLs. This tool supports downloading from both Bunkr albums and individual file URLs, while also logging any issues encountered during the download process.

## Features

- Download pictures and videos from specified URLs.
- Handles both single file and album downloads.
- Logs URLs that encounter errors for troubleshooting.
- Progress indication during downloads.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Lysagxra/SimpleLinuxBunkrDownloader.git

2. Navigate to the project directory:
   ```bash
   cd SimpleLinuxBunkrDownloader

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt

4. Ensure you have Playwright installed and set up installing Firefox:
   ```bash
   playwright install firefox

## Usage

To use the downloader, run the script with a valid album or media URL:
```bash
python3 downloader.py <bunkr_url>
```

## Example
```bash
python3 downloader.py https://bunkr.si/a/PUK068QE
```

## Batch Download

To batch download media from multiple URLs, you can use the `start.sh` script. This script reads URLs from a file named `URLs.txt` and downloads each one using the media downloader.

### Usage

1. If you are on Linux, create a file named `URLs.txt` in the root of your project, listing each URL on a new line.

2. Run the batch download script:
```bash
chmod +x start.sh  # Make the script executable
./start.sh
```
3. The downloaded files will be saved in the `Downloads` directory.

## Logging

The application logs any issues encountered during the download process in a file named `session_log.txt`. Check this file for any URLs that may have been blocked or had errors.
