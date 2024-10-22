# Linux Media Downloader

A Python-based media downloader that utilizes Playwright for browser automation to fetch and download images and videos from specified URLs. This tool supports downloading from various media platforms and logs any issues encountered during the download process.

## Features

- Download pictures and videos from specified URLs.
- Handles both single file and album downloads.
- Logs URLs that encounter errors for troubleshooting.
- Progress indication during downloads.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Lysagxra/LinuxBunkrDownloader.git

2. Navigate to the project directory:
   ```bash
   cd LinuxBunkrDownloader

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt

4. Ensure you have Playwright installed and set up installing Firefox:
   ```bash
   playwright install firefox

## Usage

To use the media downloader, run the script with a valid album or media URL:
```bash
python3 downloader.py <album_or_media_url>
```

## Example
```bash
python3 downloader.py https://bunkr.si/a/PUK068QE
```

## Logging

The application logs any issues encountered during the download process in a file named session_log.txt. Check this file for any URLs that may have been blocked or had errors.

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.
