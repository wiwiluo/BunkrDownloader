"""Python-based downloader for Bunkr albums and files.

Usage:
    Run the script from the command line with a valid album or media URL:
        python3 downloader.py <album_or_media_url>
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from argparse import Namespace
from typing import TYPE_CHECKING

from requests.exceptions import ConnectionError as RequestConnectionError
from requests.exceptions import RequestException, Timeout

from helpers.bunkr_utils import get_bunkr_status
from helpers.crawlers.crawler_utils import extract_item_pages, get_download_info
from helpers.downloaders.album_downloader import AlbumDownloader, MediaDownloader
from helpers.general_utils import (
    clear_terminal,
    create_download_directory,
    fetch_page,
    format_directory_name,
)
from helpers.managers.live_manager import LiveManager
from helpers.managers.log_manager import LoggerTable
from helpers.managers.progress_manager import ProgressManager
from helpers.url_utils import (
    check_url_type,
    get_album_id,
    get_album_name,
    get_host_page,
    get_identifier,
)

if TYPE_CHECKING:
    from bs4 import BeautifulSoup


async def handle_download_process(
    bunkr_status: dict[str, str],
    page_info: tuple[str, BeautifulSoup],
    download_path: str,
    live_manager: LiveManager,
    args: Namespace,
) -> None:
    """Handle the download process for a Bunkr album or a single item."""
    url, soup = page_info
    host_page = get_host_page(url)
    identifier = get_identifier(url)

    if check_url_type(url):
        item_pages = extract_item_pages(soup, host_page)
        album_downloader = AlbumDownloader(
            session_info=(bunkr_status, download_path),
            album_info=(identifier, item_pages),
            live_manager=live_manager,
            args=args,
        )
        await album_downloader.download_album()

    else:
        download_link, file_name = await get_download_info(url, soup)
        live_manager.add_overall_task(identifier, num_tasks=1)
        task = live_manager.add_task()

        downloader = MediaDownloader(
            session_info=(bunkr_status, download_path),
            download_info=(download_link, file_name, task),
            live_manager=live_manager,
        )
        downloader.download()


async def validate_and_download(
    bunkr_status: dict[str, str],
    url: str,
    live_manager: LiveManager,
    args: Namespace | None = None,
) -> None:
    """Validate the provided URL, and initiate the download process."""
    soup = await fetch_page(url)

    album_id = get_album_id(url) if check_url_type(url) else None
    album_name = get_album_name(soup)

    directory_name = format_directory_name(album_name, album_id)
    download_path = create_download_directory(directory_name)

    try:
        await handle_download_process(
            bunkr_status,
            (url, soup),
            download_path,
            live_manager,
            args=args,
        )

    except (RequestConnectionError, Timeout, RequestException) as err:
        error_message = f"Error downloading from {url}: {err}"
        raise RuntimeError(error_message) from err


def initialize_managers(*, disable_ui: bool = False) -> LiveManager:
    """Initialize and return the managers for progress tracking and logging."""
    progress_manager = ProgressManager(task_name="Album", item_description="File")
    logger_table = LoggerTable()
    return LiveManager(progress_manager, logger_table, disable_ui=disable_ui)


def parse_arguments() -> Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Acquire URL and other arguments.")
    parser.add_argument("url", type=str, help="The URL to process")
    parser.add_argument(
        "--ignore",
        type=str,
        nargs="+",
        help="A list of substrings to match against filenames. "
        "Files containing any of these substrings in their names will be skipped.",
    )
    parser.add_argument(
        "--include",
        type=str,
        nargs="+",
        help="A list of substrings to match against filenames. "
        "Files containing any of these substrings in their names will be downloaded.",
    )
    parser.add_argument(
        "--disable-ui",
        action="store_true",
        help="Disable the user interface",
    )
    return parser.parse_args()


async def main() -> None:
    """Initialize the download process."""
    clear_terminal()
    bunkr_status = get_bunkr_status()
    args = parse_arguments()
    live_manager = initialize_managers(disable_ui=args.disable_ui)

    try:
        with live_manager.live:
            await validate_and_download(
                bunkr_status,
                args.url,
                live_manager,
                args=args,
            )
            live_manager.stop()

    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
