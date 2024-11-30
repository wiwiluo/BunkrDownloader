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
from helpers.managers.log_manager import LoggerTable
from helpers.managers.live_manager import LiveManager
from helpers.managers.progress_manager import ProgressManager
from downloader import validate_and_download, clear_terminal

FILE = "URLs.txt"
SESSION_LOG = "session_log.txt"

async def process_urls(urls):
    """
    Validates and downloads items for a list of URLs.

    Args:
        urls (list): A list of URLs to process.
    """
    bunkr_status = get_bunkr_status()

    progress_manager = ProgressManager(item_description="File")
    progress_table = progress_manager.create_progress_table()

    logger_table = LoggerTable()
    live_manager = LiveManager(progress_table, logger_table)

    try:
        with live_manager.live:
            for url in urls:
                await validate_and_download(
                    bunkr_status, url, progress_manager, live_manager
                )

    except KeyboardInterrupt:
        sys.exit(1)

async def main():
    """
    Main function to execute the script.

    Clears the session log, reads URLs from a file, processes them,
    and clears the URLs file at the end.
    """
    clear_terminal()
    write_file(SESSION_LOG)

    urls = read_file(FILE)
    await process_urls(urls)

    write_file(FILE)

if __name__ == '__main__':
    asyncio.run(main())
