"""
Python-based downloader for Bunkr albums and files, supporting single-file and
album downloads with error logging.

Usage:
    Run the script from the command line with a valid album or media URL:
        python3 downloader.py <album_or_media_url>
"""

import sys
import asyncio
import argparse

from requests.exceptions import (
    ConnectionError as RequestConnectionError,
    Timeout, RequestException
)

from helpers.managers.live_manager import LiveManager
from helpers.managers.log_manager import LoggerTable
from helpers.managers.progress_manager import ProgressManager

from helpers.downloaders.album_downloader import AlbumDownloader
from helpers.downloaders.album_downloader import MediaDownloader

from helpers.crawlers.crawler_utils import (
    extract_item_pages,
    get_download_info
)

from helpers.bunkr_utils import get_bunkr_status
from helpers.general_utils import (
    fetch_page,
    create_download_directory,
    clear_terminal,
    format_directory_name
)
from helpers.url_utils import (
    check_url_type,
    get_identifier,
    get_album_name,
    get_album_id,
    get_host_page,
)

async def handle_download_process(
    bunkr_status, page_info, download_path, live_manager, args
):
    """
    Handles the download process for a Bunkr album or a single item.

    Args:
        bunkr_status (dict): Current status of Bunkr subdomains.
        page_info (tuple): Contains details of the page to process:
            - url (str): The URL of the item or album to download.
            - soup (BeautifulSoup): Parsed HTML content of the page.
        download_path (str): The directory path where downloaded files will be
                             saved.
        live_manager (LiveManager): Manages the live display and updates
                                    during the download process.
    """
    (url, soup) = page_info
    host_page = get_host_page(url)
    identifier = get_identifier(url)

    if check_url_type(url):
        item_pages = extract_item_pages(soup, host_page)
        album_downloader = AlbumDownloader(
            session_info=(bunkr_status, download_path),
            album_info=(identifier, item_pages),
            live_manager=live_manager,
            args=args
        )
        await album_downloader.download_album()

    else:
        download_link, file_name = await get_download_info(soup)
        live_manager.add_overall_task(identifier, num_tasks=1)
        task = live_manager.add_task()

        downloader = MediaDownloader(
            session_info=(bunkr_status, download_path),
            download_info=(download_link, file_name, task),
            live_manager=live_manager,
        )
        downloader.download()

async def validate_and_download(bunkr_status, url, live_manager, args=None):
    """
    Validates the provided URL, prepares the download directory, and initiates
    the download process.

    Args:
        bunkr_status (object): The session status or context used for managing
                               the download process.
        url (str): The URL to validate and download content from.
        live_manager (object): An object for managing live progress updates
                               and task states.

    Raises:
        RequestConnectionError: If there is a connection error during the
                                download process.
        Timeout: If the request times out while processing the URL.
        RequestException: If there is a general request-related error.
    """
    soup = await fetch_page(url)

    album_id = (
        get_album_id(url) if check_url_type(url)
        else None
    )
    album_name = get_album_name(soup)

    directory_name = format_directory_name(album_name, album_id)
    download_path = create_download_directory(directory_name)

    try:
        await handle_download_process(
            bunkr_status,
            (url, soup),
            download_path,
            live_manager,
            args=args
        )

    except (RequestConnectionError, Timeout, RequestException) as err:
        print(f"Error downloading from {url}: {err}")

def initialize_managers():
    """
    Initializes and returns the managers for progress tracking and logging.

    Returns:
        LiveManager: Handles the live display of progress and logs.
    """
    progress_manager = ProgressManager(
        task_name = "Album",
        item_description="File"
    )
    logger_table = LoggerTable()
    return LiveManager(progress_manager, logger_table)

def parse_arguments():
    """
    Parses command-line arguments for the URL, an optional ignore list, and an
    optional include list.

    Returns:
        Namespace: Parsed arguments, including:
            - url (str): The URL to process (required).
            - ignore_list (list of str): A list of substrings; files whose
                                         names contain any of these substrings
                                         will be skipped (optional).
            - include_list (list of str): A list of substrings; files whose
                                         names contain any of these substrings
                                         will only be downloaded (optional).
    """
    parser = argparse.ArgumentParser(
        description='Acquire URL and other arguments.'
    )
    parser.add_argument(
        'url',
        type=str,
        help='The URL to process'
    )
    parser.add_argument(
        '--ignore',
        type=str,
        nargs='+',
        help='A list of substrings to match against filenames. '
             'Files containing any of these substrings '
             'in their names will be skipped.'
    )
    parser.add_argument(
        '--include',
        type=str,
        nargs='+',
        help='A list of substrings to match against filenames. '
             'Files containing any of these substrings '
             'in their names will be downloaded.'
    )
    args = parser.parse_args()
    return args

async def main():
    """
    Main function for initiating the download process.
    """
    clear_terminal()
    bunkr_status = get_bunkr_status()
    live_manager = initialize_managers()
    args = parse_arguments()

    try:
        with live_manager.live:
            await validate_and_download(
                bunkr_status,
                args.url,
                live_manager,
                args=args
            )
            live_manager.stop()

    except KeyboardInterrupt:
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
