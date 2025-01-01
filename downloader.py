"""
Python-based downloader for Bunkr albums and files. Leverages Playwright for
browser automation, supporting single-file and album downloads with error logging.

Usage:
    Run the script from the command line with a valid album or media URL:
        python3 downloader.py <album_or_media_url>
"""

import os
import sys
import time
import random
import asyncio
from asyncio import Semaphore

import requests
from requests.exceptions import (
    ConnectionError as RequestConnectionError,
    Timeout, RequestException
)

from helpers.crawlers.crawler_utils import extract_item_pages, get_download_info

from helpers.managers.live_manager import LiveManager
from helpers.managers.log_manager import LoggerTable
from helpers.managers.progress_manager import ProgressManager

from helpers.download_utils import save_file_with_progress
from helpers.file_utils import write_on_session_log
from helpers.bunkr_utils import (
    get_bunkr_status, subdomain_is_offline, mark_subdomain_as_offline
)
from helpers.general_utils import (
    fetch_page, create_download_directory, clear_terminal
)
from helpers.url_utils import (
    check_url_type, get_identifier, get_album_id, validate_item_page
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) "
        "Gecko/20100101 Firefox/117.0"
    ),
    "Connection": "keep-alive",
    "Referer": "https://get.bunkrr.su/"
}

class MediaDownloader:
    """
    Manages the downloading of individual files from Bunkr URLs, with support
    for retries and progress updates.

    Attributes:
        bunkr_status (dict): Status of Bunkr subdomains.
        download_path (str): Path where the file will be saved.
        download_link (str): URL of the file to be downloaded.
        file_name (str): Name of the file being downloaded.
        task (str): Task ID associated with the file download.
        live_manager (LiveManager): Handles live display of progress and logs.
        retries (int): Maximum number of retry attempts for failed downloads.
    """

    def __init__(self, session_info, download_info, live_manager, retries=5):
        self.bunkr_status, self.download_path = session_info
        self.download_link, self.file_name, self.task = download_info
        self.live_manager = live_manager
        self.retries = retries

    def handle_request_exception(self, req_err, attempt):
        """Handles exceptions during the request and manages retries."""
        if req_err.response is None:
            # Mark the subdomain as offline and exit the loop
            marked_subdomain = mark_subdomain_as_offline(
                self.bunkr_status, self.download_link
            )
            self.live_manager.update_log(
                "No response",
                f"Subdomain {marked_subdomain} has been marked as offline."
            )
            return False

        if req_err.response.status_code == 429:
            self.live_manager.update_log(
                "Too many requests",
                f"Retrying to download {self.file_name}... "
                f"({attempt + 1}/{self.retries})"
            )
            if attempt < self.retries - 1:
                # Retry the request
                delay = 4 ** (attempt + 1) + random.uniform(2, 4)
                time.sleep(delay)
                return True

        # Do not retry, exit the loop
        return False

    def check_and_skip_existing_file(self, final_path):
        """Check if the file already exists. If so, skip the download."""
        if os.path.exists(final_path):
            self.live_manager.update_log(
                "Skipped download",
                f"{self.file_name} has already been downloaded."
            )
            self.live_manager.update_task(
                self.task, completed=100, visible=False
            )
            return True
        return False

    def attempt_download(self, final_path):
        """Attempt to download the file with retries."""
        for attempt in range(self.retries):
            try:
                response = requests.get(
                    self.download_link,
                    stream=True,
                    headers=HEADERS,
                    timeout=30
                )
                response.raise_for_status()

                # Exit the loop if the download is successful
                save_file_with_progress(
                    response, final_path, self.task, self.live_manager
                )
                return False

            except requests.RequestException as req_err:
                # Exit the loop if not retrying
                if not self.handle_request_exception(req_err, attempt):
                    break
        return True

    def handle_failed_download(self, retry_failed):
        """Handle a failed download after all retry attempts."""
        if not retry_failed:
            self.live_manager.update_log(
                "Exceeded retry attempts",
                f"Exceeded retry attempts for {self.file_name}. "
                "It will be retried one more time after all other tasks."
            )
            return {
                'id': self.task,
                'file_name': self.file_name,
                'download_link': self.download_link
            }

        self.live_manager.update_log(
            "Download failed",
            f"Failed to download {self.file_name}. "
            "The failure has been logged."
        )
        self.live_manager.update_task(self.task, visible=False)
        return None

    def download(self):
        """Main method to handle the download process."""
        retry_failed = self.retries == 1
        if subdomain_is_offline(self.download_link, self.bunkr_status) and \
            retry_failed:
            self.live_manager.update_log(
                "Non-operational subdomain",
                f"The subdomain for {self.file_name} appears to be offline. "
                "Check the log file."
            )
            write_on_session_log(self.download_link)
            self.live_manager.update_task(self.task, visible=False)
            return None

        final_path = os.path.join(self.download_path, self.file_name)

        # Check if the file already exists and skip if it does
        if self.check_and_skip_existing_file(final_path):
            return None

        # Attempt to download the file with retries
        failed_download = self.attempt_download(final_path)

        # Handle failed download after retries
        if failed_download:
            return self.handle_failed_download(retry_failed)
        return None

class AlbumDownloader:
    """
    Manages the downloading of entire Bunkr albums, including tracking progress
    and handling failed downloads.

    Attributes:
        bunkr_status (dict): Status of Bunkr subdomains.
        download_path (str): Directory where the album will be saved.
        album_id (str): ID of the album being downloaded.
        item_pages (list): List of item pages in the album.
        live_manager (LiveManager): Handles live display of progress and logs.
        failed_downloads (list): List of downloads that failed during the
                                 process.
    """

    def __init__(self, session_info, album_info, live_manager):
        self.bunkr_status, self.download_path = session_info
        self.album_id, self.item_pages = album_info
        self.live_manager = live_manager
        self.failed_downloads = []

    async def execute_item_download(self, item_page, current_task, semaphore):
        """Handles the download of an individual item in the album."""
        async with semaphore:
            task = self.live_manager.add_task(current_task=current_task)

            # Process the download of an item
            validated_item_page = validate_item_page(item_page)
            item_soup = await fetch_page(validated_item_page)
            (item_download_link, item_file_name) = await get_download_info(
                item_soup, validated_item_page
            )

            # Download item
            if item_download_link:
                downloader = MediaDownloader(
                    session_info=(self.bunkr_status, self.download_path),
                    download_info=(item_download_link, item_file_name, task),
                    live_manager=self.live_manager
                )

                failed_download = await asyncio.to_thread(downloader.download)
                if failed_download:
                    self.failed_downloads.append(failed_download)

    async def retry_failed_download(self, task, file_name, download_link):
        """Handles failed downloads and retries them."""
        downloader = MediaDownloader(
            session_info=(self.bunkr_status, self.download_path),
            download_info=(download_link, file_name, task),
            live_manager=self.live_manager,
            retries=1  # Retry once for failed downloads
        )
        # Run the synchronous download function in a separate thread
        await asyncio.to_thread(downloader.download)

    async def process_failed_downloads(self):
        """Processes any failed downloads after the initial attempt."""
        for data in self.failed_downloads:
            await self.retry_failed_download(
                data['id'],
                data['file_name'],
                data['download_link']
            )
        self.failed_downloads.clear()

    async def download_album(self, max_workers=5):
        """Main method to handle the album download."""
        num_tasks = len(self.item_pages)
        self.live_manager.add_overall_task(
            description=self.album_id,
            num_tasks=num_tasks
        )

        # Create tasks for downloading each item in the album
        semaphore = Semaphore(max_workers)
        tasks = [
            self.execute_item_download(item_page, current_task, semaphore)
            for current_task, item_page in enumerate(self.item_pages)
        ]
        await asyncio.gather(*tasks)

        # If there are failed downloads, process them after all downloads are
        # complete
        if self.failed_downloads:
            await self.process_failed_downloads()

async def handle_download_process(
    bunkr_status, page_info, download_path, live_manager
):
    """
    Handles the download process for a Bunkr album or single item.

    Args:
        bunkr_status (dict): Current status of Bunkr subdomains.
        page_info (tuple): A tuple containing:
            - url (str): The URL of the item or album to download.
            - soup (BeautifulSoup): The parsed HTML content of the page.
        download_path (str): Path to save the downloaded files.
        live_manager (LiveManager): The live display manager that handles
                                    updating the live view of the download
                                    process.
    """
    (url, soup) = page_info
    identifier = get_identifier(url)

    if check_url_type(url):
        item_pages = extract_item_pages(soup)
        album_downloader = AlbumDownloader(
            session_info=(bunkr_status, download_path),
            album_info=(identifier, item_pages),
            live_manager=live_manager
        )
        await album_downloader.download_album()

    else:
        (download_link, file_name) = await get_download_info(soup, url)
        live_manager.add_overall_task(identifier, num_tasks=1)
        task = live_manager.add_task()

        downloader = MediaDownloader(
            session_info=(bunkr_status, download_path),
            download_info=(download_link, file_name, task),
            live_manager=live_manager,
        )
        downloader.download()

async def validate_and_download(bunkr_status, url, live_manager):
    """
    Validates the provided URL, fetches the associated page, and initiates
    the download process for the album or item.

    Args:
        bunkr_status (dict): A dictionary representing the current status
                             of Bunkr subdomains, used for checking the
                             availability of necessary resources.
        url (str): The URL of the album or item to download. This URL will 
                   be validated and used to fetch the associated page content.
        live_manager (LiveManager): The live display manager that handles
                                    updating the live view of the download
                                    process.

    Raises:
        RequestConnectionError: If there is a network error while making the
                                request.
        Timeout: If the request times out while trying to fetch data.
        RequestException: If there is any other exception related to the
                          request.
    """
    validated_url = validate_item_page(url)
    soup = await fetch_page(validated_url)
    album_id = (
        get_album_id(validated_url) if check_url_type(validated_url)
        else None
    )
    download_path = create_download_directory(album_id)

    try:
        await handle_download_process(
            bunkr_status,
            (validated_url, soup),
            download_path,
            live_manager
        )

    except (RequestConnectionError, Timeout, RequestException) as err:
        print(f"Error downloading the from {validated_url}: {err}")

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

async def main():
    """
    Main function for initiating the download process.
    """
    if len(sys.argv) != 2:
        script_name = os.path.basename(__file__)
        print(f"Usage: python3 {script_name} <album_url>")
        sys.exit(1)

    clear_terminal()
    bunkr_status = get_bunkr_status()
    live_manager = initialize_managers()
    url = sys.argv[1]

    try:
        with live_manager.live:
            await validate_and_download(bunkr_status, url, live_manager)
            live_manager.stop()

    except KeyboardInterrupt:
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
