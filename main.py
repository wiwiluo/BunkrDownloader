"""
This module provides functionality to read URLs from a specified file,
validate them, and download the associated content. It manages the entire
download process by leveraging asynchronous operations, allowing for
efficient handling of multiple URLs.

Usage:
    To run the module, execute the script directly. It will process URLs
    listed in 'URLs.txt' and log the session activities in 'session_log.txt'.
"""

import sys
import asyncio

from helpers.bunkr_utils import get_bunkr_status
from helpers.file_utils import read_file, write_file
from helpers.general_utils import clear_terminal
from helpers.config import FILE, SESSION_LOG

from downloader import validate_and_download, initialize_managers

async def process_urls(urls):
    """
    Validates and downloads items for a list of URLs.

    Args:
        urls (list): A list of URLs to process.
    """
    bunkr_status = get_bunkr_status()
    live_manager = initialize_managers()

    try:
        with live_manager.live:
            for url in urls:
                await validate_and_download(bunkr_status, url, live_manager)
            live_manager.stop()

    except KeyboardInterrupt:
        sys.exit(1)

async def main():
    """
    Main function to execute the script.
    """
    # Clear the terminal and session log file
    clear_terminal()
    write_file(SESSION_LOG)

    # Read and process URLs
    urls = read_file(FILE)
    await process_urls(urls)

    # Clear URLs file
    write_file(FILE)

if __name__ == '__main__':
    asyncio.run(main())
