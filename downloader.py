"""
A Python-based Bunkr downloader that utilizes Playwright for browser automation
to fetch and download from Bunkr albums and single file URLs.
This tool supports both single file and album downloads, while also logging any
issues encountered during the download process.

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

from helpers.playwright_crawler import extract_media_download_link
from helpers.download_utils import save_file_with_progress
from helpers.file_utils import write_on_session_log
from helpers.managers.log_manager import LoggerTable
from helpers.managers.live_manager import LiveManager
from helpers.managers.progress_manager import ProgressManager
from helpers.url_utils import (
    check_url_type, get_identifier, get_album_id,
    validate_item_page, get_item_type
)
from helpers.bunkr_utils import (
    get_bunkr_status, subdomain_is_offline, mark_subdomain_as_offline
)
from helpers.general_utils import (
    fetch_page, create_download_directory, clear_terminal
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) "
        "Gecko/20100101 Firefox/117.0"
    ),
    "Connection": "keep-alive",
    "Referer": "https://get.bunkrr.su/"
}

class Downloader:
    """
    Manages the downloading of individual files from Bunkr URLs.

    Attributes:
        bunkr_status (dict): Current status of Bunkr subdomains.
        download_info (tuple): Contains the download link, download path,
                               and file name for the current file.
        progress_info (tuple): Contains the task ID and ProgressManager
                               instance for managing progress.
        retries (int): Number of retry attempts allowed for failed downloads.
    """

    def __init__(
        self, bunkr_status, download_info, progress_info, live_manager,
        retries=5
    ):
        """
        Initializes the Downloader instance with download and progress details.
        """
        self.bunkr_status = bunkr_status
        self.download_link, self.download_path, self.file_name = download_info
        self.task, self.progress_manager = progress_info
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
            self.progress_manager.update_task(
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
                    response, final_path, self.task, self.progress_manager
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
                "Download marked as failed",
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
        self.progress_manager.update_task(self.task, visible=False)
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
            self.progress_manager.update_task(self.task, visible=False)
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
    Manages the downloading of entire Bunkr albums.

    Attributes:
        bunkr_status (dict): Current status of Bunkr subdomains.
        album_info (tuple): Contains the album ID and item pages.
        download_path (str): Directory to save the album.
        progress_manager (ProgressManager): Manages progress for the album.
    """

    def __init__(
        self, bunkr_status, album_info, download_path,
        progress_manager, live_manager
    ):
        self.bunkr_status = bunkr_status
        self.album_id, self.item_pages = album_info
        self.download_path = download_path
        self.progress_manager = progress_manager
        self.live_manager = live_manager
        self.failed_downloads = []

    async def execute_item_download(self, item_page, current_task, semaphore):
        """Handles the download of an individual item in the album."""
        async with semaphore:
            task = self.progress_manager.add_task(current_task=current_task)

            # Process the download of an item
            validated_item_page = validate_item_page(item_page)
            item_soup = await fetch_page(validated_item_page)
            (item_download_link, item_file_name) = await get_download_info(
                item_soup, validated_item_page
            )

            # Download item
            if item_download_link:
                downloader = Downloader(
                    bunkr_status=self.bunkr_status,
                    download_info=(
                        item_download_link,
                        self.download_path,
                        item_file_name
                    ),
                    progress_info=(task, self.progress_manager),
                    live_manager=self.live_manager
                )

                failed_download = await asyncio.to_thread(downloader.download)
                if failed_download:
                    self.failed_downloads.append(failed_download)

    async def retry_failed_download(self, task, file_name, download_link):
        """Handles failed downloads and retries them."""
        downloader = Downloader(
            bunkr_status=self.bunkr_status,
            download_info=(download_link, self.download_path, file_name),
            progress_info=(task, self.progress_manager),
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
        num_items = len(self.item_pages)
        self.progress_manager.add_overall_task(
            description=self.album_id,
            num_tasks=num_items
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

async def extract_with_playwright(url):
    """
    Initiates the download process for the specified URL using Playwright.

    Args:
        url (str): The URL of the media to download.

    Returns:
        str or None: The download link if successful, or None if an error
                     occurs.
    """
    item_type = get_item_type(url)
    media_type_mapping = {'v': 'video', 'i': 'picture'}

    if item_type not in media_type_mapping:
        print(
            f"Unknown item type: {item_type}. "
            f"Supported types are: {list(media_type_mapping.keys())}."
        )
        return None

    media_type = media_type_mapping[item_type]
    return await extract_media_download_link(url, media_type)

def extract_item_pages(soup):
    """
    Extracts individual item page URLs from the parsed HTML content.

    Args:
        soup (BeautifulSoup): The BeautifulSoup object representing the parsed
                              HTML content of the page.

    Returns:
        list: A list of URLs (strings) for individual item pages. If no item
              pages are found or an error occurs, an empty list is returned.

    Raises:
        AttributeError: If there is an error accessing the required attributes
                        of the HTML elements, such as missing or invalid tags.
    """
    try:
        items = soup.find_all(
            'a',
            {
                'class': "after:absolute after:z-10 after:inset-0",
                'href': True
            }
        )
        return [item['href'] for item in items]

    except AttributeError as attr_err:
        print(f"Error extracting item pages: {attr_err}")

    return []

def get_item_download_link(item_soup, item_type):
    """
    Retrieves the download link for a specific item (video or picture) from its
    HTML content.

    Args:
        item_soup (BeautifulSoup): The BeautifulSoup object representing the
                                   parsed HTML content of the item.
        item_type (str): The type of the item.

    Returns:
        str: The download link (URL) for the item. Returns `None` if the link
             cannot be found.

    Raises:
        AttributeError: If the required `src` attribute is not found for the
                        specified `item_type`.
        UnboundLocalError: If there is an issue with the assignment of
                           `item_container` in the case of unknown `item_type`.
    """
    try:
        if item_type in ('v', 'd'):
            item_container = item_soup.find('source', {'src': True})
        else:
            item_container = item_soup.find(
                'img',
                {
                    'class': "max-h-full w-auto object-cover relative z-20",
                    'src': True
                }
            )
        return item_container['src']

    except (AttributeError, UnboundLocalError) as err:
        print(f"Error extracting source: {err}")

    return None

async def get_download_info(item_soup, item_page):
    """
    Gathers download information (link and filename) for the item.

    Args:
        item_soup (BeautifulSoup): Parsed HTML content of the item.
        item_page (str): The item page URL.

    Returns:
        tuple: A tuple containing the download link and file name.
    """
    validated_item_page = validate_item_page(item_page)
    if item_soup is None:
        return await extract_with_playwright(validated_item_page)

    item_type = get_item_type(validated_item_page)
    item_download_link = get_item_download_link(item_soup, item_type)

    item_file_name = (
        item_download_link.split('/')[-1] if item_download_link
        else None
    )

    return item_download_link, item_file_name

async def handle_download_process(
    bunkr_status, page_info, download_path, progress_manager, live_manager
):
    """
    Handles the download process for a Bunkr album or single item.

    Args:
        bunkr_status (dict): Current status of Bunkr subdomains.
        page_info (tuple): A tuple containing:
            - url (str): The URL of the item or album to download.
            - soup (BeautifulSoup): The parsed HTML content of the page.
        download_path (str): Path to save the downloaded files.
        progress_manager (ProgressManager): Manager for tracking progress.
        live_manager (LiveManager): The live display manager that handles
                                    updating the live view of the download
                                    process.
    """
    (url, soup) = page_info
    identifier = get_identifier(url)

    if check_url_type(url):
        item_pages = extract_item_pages(soup)
        album_downloader = AlbumDownloader(
            bunkr_status=bunkr_status,
            album_info=(identifier, item_pages),
            download_path=download_path,
            progress_manager=progress_manager,
            live_manager=live_manager
        )
        await album_downloader.download_album()

    else:
        (download_link, file_name) = await get_download_info(soup, url)
        progress_manager.add_overall_task(identifier, num_tasks=1)
        task = progress_manager.add_task()

        downloader = Downloader(
            bunkr_status=bunkr_status,
            download_info=(download_link, download_path, file_name),
            progress_info=(task, progress_manager),
            live_manager=live_manager
        )
        downloader.download()

async def validate_and_download(
    bunkr_status, url, progress_manager, live_manager
):
    """
    Validates the provided URL, fetches the associated page, and initiates
    the download process for the album or item.

    Args:
        bunkr_status (dict): A dictionary representing the current status
                             of Bunkr subdomains, used for checking the
                             availability of necessary resources.
        url (str): The URL of the album or item to download. This URL will 
                   be validated and used to fetch the associated page content.
        progress_manager (ProgressManager): Manager for tracking progress.
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

    try:
        download_path = create_download_directory(album_id)
        await handle_download_process(
            bunkr_status,
            (validated_url, soup),
            download_path,
            progress_manager,
            live_manager
        )

    except (RequestConnectionError, Timeout, RequestException) as err:
        print(f"Error downloading the from {validated_url}: {err}")

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
    url = sys.argv[1]

    progress_manager = ProgressManager(item_description="File")
    progress_table = progress_manager.create_progress_table()

    logger_table = LoggerTable()
    live_manager = LiveManager(progress_table, logger_table)

    try:
        with live_manager.live:
            await validate_and_download(
                bunkr_status, url, progress_manager, live_manager
            )

    except KeyboardInterrupt:
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
