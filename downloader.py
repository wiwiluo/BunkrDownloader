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

import requests
from rich.live import Live
from requests.exceptions import (
    ConnectionError as RequestConnectionError,
    Timeout, RequestException
)

from helpers.playwright_downloader import extract_media_download_link
from helpers.file_utils import write_on_session_log
from helpers.download_utils import save_file_with_progress
from helpers.bunkr_utils import (
    check_url_type, get_album_id, validate_item_page, get_item_type,
    subdomain_is_non_operational, get_identifier
)
from helpers.progress_utils import (
    truncate_description, create_progress_bar, create_progress_table
)
from helpers.general_utils import (
    fetch_page, create_download_directory, clear_terminal
)

SCRIPT_NAME = os.path.basename(__file__)
TASK_COLOR = "light_cyan3"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) "
        "Gecko/20100101 Firefox/117.0"
    ),
    "Connection": "keep-alive",
    "Referer": "https://get.bunkrr.su/"
}

def extract_with_playwright(url):
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
    return extract_media_download_link(url, media_type)

def download(download_link, download_path, file_name, task_info, retries=3):
    """
    Downloads a file from the specified download link and saves it to the given
    directory with the provided file name.

    Args:
        download_link (str): The URL to download the file from.
        download_path (str): The directory where the file will be saved.
        file_name (str): The name to save the downloaded file as.
        task_info (tuple): A tuple containing progress tracking information:
            - job_progress: The progress bar object for tracking the download.
            - task: The specific task being tracked.
            - overall_task: The overall task tracking the progress of download
                            process.
        retries (int, optional): The number of retry attempts if the download
                                 fails (default is 3).

    Raises:
        requests.RequestException: If there are issues with the HTTP request.
    """
    def handle_request_exception(req_err, attempt, retries):
        """Handles exceptions during the request and manages retries."""
        if req_err.response is None:
            # Do not retry, exit the loop
            print(f"Request failed with no response: {req_err}")
            return False

        if req_err.response.status_code == 429:
            print(
                "Too many requests. Retrying in a moment... "
                f"({attempt + 1}/{retries})"
            )
            if attempt < retries - 1:
                # Retry the request
                time.sleep(20)
                return True
        else:
            # Do not retry, exit the loop
            print(f"Error during download: {req_err}")
            return False

        return False

    if subdomain_is_non_operational(download_link):
        print("Non-operational subdomain, check the log file")
        write_on_session_log(download_link)
        return

    final_path = os.path.join(download_path, file_name)
    (_, _, overall_progress, overall_task) = task_info

    for attempt in range(retries):
        try:
            response = requests.get(
                download_link, stream=True, headers=HEADERS, timeout=90
            )
            response.raise_for_status()

            # Exit the loop if the download is successful
            save_file_with_progress(response, final_path, task_info)
            overall_progress.advance(overall_task)
            return

        except requests.RequestException as req_err:
            if not handle_request_exception(req_err, attempt, retries):
                # Exit the loop if not retrying
                return

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

def get_download_info(item_soup, item_page):
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
        return extract_with_playwright(validated_item_page)

    item_type = get_item_type(validated_item_page)
    item_download_link = get_item_download_link(item_soup, item_type)

    item_file_name = (
        item_download_link.split('/')[-1] if item_download_link
        else None
    )

    return item_download_link, item_file_name

def process_item_download(item_page, download_path, task_info):
    """
    Processes the download of a single item from the specified item page.

    Args:
        item_page (str): The URL of the item page to download.
        download_path (str): The path where the downloaded file will be saved.
        task_info (tuple): A tuple containing job progress, task, and other
                          info.
    """
    validated_item_page = validate_item_page(item_page)
    item_soup = fetch_page(validated_item_page)
    (item_download_link, item_file_name) = get_download_info(
        item_soup, validated_item_page
    )

    if item_download_link:
        download(item_download_link, download_path, item_file_name, task_info)

def download_album(
    album_id, item_pages, download_path, progress_info, visible_tasks=4
):
    """
    Downloads all items in an album from a list of item pages and tracks the
    download progress.

    Args:
        album_id (str): The unique identifier for the album being downloaded.
        item_pages (list): A list of URLs corresponding to each item to be
                           downloaded.
        download_path (str): The local directory path where the downloaded
                             files will be saved.
        overall_progress (Progress): The overall progress tracker that manages
                                     all tasks related to the album.
        job_progress (Progress): A progress tracker specifically for individual 
                                 item downloads.
    """
    (overall_progress, job_progress) = progress_info
    num_items = len(item_pages)
    overall_task = overall_progress.add_task(
       f"[{TASK_COLOR}]{album_id}", total=num_items
    )

    active_tasks = []
    for (indx, item_page) in enumerate(item_pages):
        task = job_progress.add_task(
            f"[{TASK_COLOR}]File {indx + 1}/{num_items}", total=100
        )
        process_item_download(
            item_page, download_path,
            (job_progress, task, overall_progress, overall_task)
        )
        active_tasks.append(task)

        # Remove the oldest active task and update
        if len(active_tasks) >= visible_tasks:
            oldest_task = active_tasks.pop(0)
            job_progress.update(oldest_task, visible=False)

    # Remove remaining tasks
    for remaining_task in active_tasks:
        job_progress.update(remaining_task, visible=False)

def handle_download_process(
    soup, url, download_path, job_progress, overall_progress
):
    """
    Handles the download process for a given URL, determining whether the URL 
    corresponds to an album or a single file, and then initiating the
    appropriate download method.

    Args:
        soup (BeautifulSoup): The parsed HTML content of the main page.
        url (str): The URL of the media to download.
        download_path (str): The local path where the downloaded files will be
                             saved.
        job_progress (Progress): A progress object for tracking individual
                                 download tasks.
        overall_progress (Progress): A progress object for tracking the overall
                                     download process.
    """
    is_album = check_url_type(url)
    identifier = get_identifier(url)

    if is_album:
        item_pages = extract_item_pages(soup)
        download_album(
            identifier, item_pages, download_path,
            (overall_progress, job_progress)
        )
    else:
        (download_link, file_name) = get_download_info(soup, url)
        overall_task = overall_progress.add_task(
            f"[{TASK_COLOR}]{truncate_description(identifier)}", total=1
        )
        task = job_progress.add_task(f"[{TASK_COLOR}]Progress", total=100)

        download(
            download_link, download_path, file_name,
            (job_progress, task, overall_progress, overall_task)
        )
        job_progress.update(task, visible=False)

def validate_and_download(url, job_progress, overall_progress):
    """
    Validates the given URL, fetches the corresponding page, and orchestrates
    the download process, updating progress for individual and overall tasks.

    Args:
        url (str): The URL to validate and download content from.
        job_progress (Progress): The progress tracker for the individual
                                 download tasks (e.g., file downloads).
        overall_progress (Progress): The overall progress tracker for the
                                     entire download process (e.g., total
                                     downloads).

    Raises:
        ValueError: If the URL is invalid or if there is an issue during the
                    download process.
        RequestConnectionError: If a network connection error occurs during
                                the download.
        Timeout: If the request times out during the download.
        RequestException: If there is a generic request-related exception.
    """
    validated_url = validate_item_page(url)
    soup = fetch_page(validated_url)
    album_id = (
        get_album_id(validated_url) if check_url_type(validated_url)
        else None
    )

    try:
        download_path = create_download_directory(album_id)
        handle_download_process(
            soup, validated_url, download_path, job_progress, overall_progress
        )

    except (RequestConnectionError, Timeout, RequestException) as err:
        print(f"Error downloading the from {validated_url}: {err}.")

def main():
    """
    This function checks the command-line arguments for the required album URL,
    validates the input, and initiates the download process for the specified
    URL.
    """
    if len(sys.argv) != 2:
        print(f"Usage: python3 {SCRIPT_NAME} <album_url>")
        sys.exit(1)

    clear_terminal()
    url = sys.argv[1]

    overall_progress = create_progress_bar()
    job_progress = create_progress_bar()
    progress_table = create_progress_table(overall_progress, job_progress)

    with Live(progress_table, refresh_per_second=10):
        validate_and_download(url, job_progress, overall_progress)

if __name__ == '__main__':
    main()
