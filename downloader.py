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
from http.client import RemoteDisconnected

import requests
from bs4 import BeautifulSoup
from rich.live import Live
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
    Timeout,
    RequestException
)

from helpers.download_utils import save_file_with_progress
from helpers.progress_utils import (
    truncate_description, create_progress_bar, create_progress_table
)
from helpers.bunkr_utils import (
    check_url_type, get_album_id, validate_item_page, get_item_type,
    subdomain_is_non_operational
)
from helpers.playwright_downloader import (
    extract_media_download_link, write_on_session_log
)

SCRIPT_NAME = os.path.basename(__file__)
DOWNLOAD_FOLDER = 'Downloads'

MAX_VISIBLE_TASKS = 4
TASK_COLOR = 'light_cyan3'
TIMEOUT = 10

SESSION = requests.Session()
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) "
        "Gecko/20100101 Firefox/117.0"
    ),
    "REFERER": 'https://get.bunkrr.su/'
}

def handle_response(url, response):
    """
    Processes the HTTP response and handles specific status codes.

    Args:
        url (str): The URL to fetch.
        response (requests.Response): The HTTP response object to process.

    Returns:
        BeautifulSoup or None: A BeautifulSoup object if the response is 
                               successful; otherwise, returns None if an
                               error status code is encountered.
    """
    if response.status_code in (500, 403):
        messages = {
            500: f"Internal server error when fetching {url}",
            403: f"DDoSGuard blocked the request to {url}"
        }
        print(f"{messages[response.status_code]}, check the log file")
        write_on_session_log(url)
        return None

    return BeautifulSoup(response.text, 'html.parser')

def fetch_page(url, retries=3):
    """
    Fetches the HTML content of a page at the given URL.

    Args:
        url (str): The URL to fetch.

    Returns:
        BeautifulSoup: Parsed HTML content of the page.

    Raises:
        requests.RequestException: If there are issues with the request.
    """
    for attempt in range(retries):
        try:
            response = SESSION.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            return handle_response(url, response)

        except RemoteDisconnected:
            print(
                "Remote end closed connection without response. "
                f"Retrying in a moment... ({attempt + 1}/{retries})"
            )
            time.sleep(5)

        except requests.RequestException as req_err:
            print(f"Request error: {req_err}")
            return None

    return None

def run(url):
    """
    Initiates the download process for the specified URL using Playwright.

    Args:
        url (str): The URL of the media to download.

    Returns:
        str or None: The download link if successful, or None if an error
                     occurs.
    """
#    print("Downloading with Playwright...")
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

def create_download_directory(url):
    """
    Creates the download directory if it does not already exist.

    Args:
        download_path (str): The path of the directory to create.

    Raises:
        SystemExit: If there is an error creating the directory.
    """
    album_id = get_album_id(url) if check_url_type(url) else None
    download_path = os.path.join(DOWNLOAD_FOLDER, album_id) if album_id \
        else DOWNLOAD_FOLDER

    os.makedirs(download_path, exist_ok=True)
    return download_path

def handle_request_exception(req_err, attempt, retries):
    """
    Handles exceptions raised during the download request.

    Args:
        req_err (requests.RequestException): The raised exception.
        attempt (int): The current attempt number.
        retries (int): The total number of allowed retries.
    """
    if req_err.response.status_code == 429:
        print(
            "Too many requests. "
            f"Retrying in a moment... ({attempt + 1}/{retries})"
        )
        time.sleep(10)
    else:
        print(f"Error during download: {req_err}")

def download(download_link, download_path, file_name, task_info, retries=3):
    """
    Downloads a file from the given download link to the specified path.

    Args:
        download_link (str): The URL to download the file from.
        download_path (str): The directory to save the downloaded file.
        file_name (str): The name to save the file as.

    Raises:
        requests.RequestException: If there are issues during the download.
    """
    if subdomain_is_non_operational(download_link):
        print("Non-operational subdomain; check the log file")
        write_on_session_log(download_link)
        return

    final_path = os.path.join(download_path, file_name)
    (_, _, overall_progress, overall_task) = task_info

    for attempt in range(retries):
        try:
            response = SESSION.get(
                download_link, stream=True, headers=HEADERS, timeout=TIMEOUT
            )
            response.raise_for_status()

            # Exit the loop if the download is successful
            save_file_with_progress(response, final_path, task_info)
            overall_progress.advance(overall_task)
            break

        except requests.RequestException as req_err:
            handle_request_exception(req_err, attempt, retries)

    # Update overall progress if download was successful
#    if attempt < retries:
#        overall_progress.advance(overall_task)

def get_identifier(url):
    """
    Extracts an identifier from the given URL. If the URL represents an album,
    it retrieves the album ID; otherwise, it returns the last segment of the
    URL.

    Args:
        url (str): The URL from which to extract the identifier.

    Returns:
        str: The extracted identifier or the original URL in case of an error.
    """
    try:
        is_album = check_url_type(url)
        return get_album_id(url) if is_album else url.split('/')[-1]

    except IndexError as indx_err:
        print(f"Error extracting the identifier: {indx_err}")

    return url

def extract_item_pages(soup):

    """
    Extracts individual item pages from the parsed HTML soup.

    Args:
        soup (BeautifulSoup): Parsed HTML content of the page.

    Returns:
        list: A list of item page URLs.
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
        print(f"\t\t[-] Error extracting item pages: {attr_err}")

    return []

def get_item_download_link(item_soup, item_type):
    """
    Retrieves the download link from the item soup based on its type.

    Args:
        item_soup (BeautifulSoup): Parsed HTML content of the item.
        item_type (str): The type of item ('v' for video, 'd' for picture).

    Returns:
        str: The download link for the item.

    Raises:
        AttributeError: If the source cannot be found in the soup.
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
        return run(validated_item_page)

    item_type = get_item_type(validated_item_page)
    item_download_link = get_item_download_link(item_soup, item_type)
    item_file_name = item_download_link.split('/')[-1] \
        if item_download_link else None

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
    album_id, item_pages, download_path, overall_progress, job_progress
):
    """
    Downloads all items in an album from a list of item pages.

    Args:
        item_pages (list): A list of item page URLs.
        download_path (str): The path to save the downloaded files.

    Raises:
        TypeError: If there is an error during the download process.
    """
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
        if len(active_tasks) >= MAX_VISIBLE_TASKS:
            oldest_task = active_tasks.pop(0)
            job_progress.update(oldest_task, visible=False)

    # Remove remaining tasks
    for remaining_task in active_tasks:
        job_progress.update(remaining_task, visible=False)

def handle_download_process(
    soup, url, download_path, job_progress, overall_progress
):
    """
    Handles the download process for a given URL, determining if it's an album
    or a single file.

    Args:
        soup (BeautifulSoup): Parsed HTML content of the main page.
        url (str): The URL of the media to download.
        download_path (str): The path to save the downloaded files.
    """
    is_album = check_url_type(url)
    identifier = get_identifier(url)

    if is_album:
        item_pages = extract_item_pages(soup)
        download_album(
            identifier, item_pages, download_path,
            overall_progress, job_progress
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
    Validates the given URL and orchestrates the download process.

    Args:
        url (str): The URL to validate and download content from.

    Raises:
        ValueError: If there is an issue with the URL or during the download
                    process.
    """
    validated_url = validate_item_page(url)
    soup = fetch_page(validated_url)

    try:
        download_path = create_download_directory(validated_url)
        handle_download_process(
            soup, validated_url, download_path, job_progress, overall_progress
        )

    except (RequestsConnectionError, Timeout, RequestException) as err:
        print(f"Error downloading the from {validated_url}: {err}.")

def main():
    """
    This function checks the command-line arguments for the required album URL,
    validates the input, and initiates the download process for the specified
    URL.

    Usage:
        This script should be run from the command line with the following
        syntax:
            python3 <script_name> <album_url>

    Raises:
        SystemExit: Exits the program if the incorrect number of command-line
                    arguments is provided.
    """
    if len(sys.argv) != 2:
        print(f"Usage: python3 {SCRIPT_NAME} <album_url>")
        sys.exit(1)

    url = sys.argv[1]

    overall_progress = create_progress_bar()
    job_progress = create_progress_bar()
    progress_table = create_progress_table(overall_progress, job_progress)

    with Live(progress_table, refresh_per_second=10):
        validate_and_download(url, job_progress, overall_progress)

if __name__ == '__main__':
    main()
