import os
import sys
import asyncio
import requests
from bs4 import BeautifulSoup

from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    DownloadColumn,
    TextColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)

from utils.playwright_downloader import (
    extract_media_download_link,
    write_on_session_log
)

SCRIPT_NAME = os.path.basename(__file__)
DOWNLOAD_FOLDER = 'Downloads'
SESSION_LOG = 'session_log.txt'
CHUNK_SIZE = 8192

COLORS = {
    'PURPLE': '\033[95m',
    'CYAN': '\033[96m',
    'DARKCYAN': '\033[36m',
    'BLUE': '\033[94m',
    'GREEN': '\033[92m',
    'YELLOW': '\033[93m',
    'RED': '\033[91m',
    'BOLD': '\033[1m',
    'UNDERLINE': '\033[4m',
    'END': '\033[0m'
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) "
        "Gecko/20100101 Firefox/117.0"
    )
}

def check_url_type(url):
    """
    Determines whether the provided URL corresponds to an album or a single
    file.

    Args:
        url (str): The URL to check.

    Returns:
        bool: True if the URL is for an album, False if it is for a single file.

    Raises:
        SystemExit: If the URL is invalid.
        ValueError: If the URL format is incorrect.
    """
    try:
        url_segment = url.split('/')[-2]
        url_mapping = {'a': True, 'v': False}

        if url_segment in url_mapping:
            return url_mapping[url_segment]

        print('\nEnter a valid URL.')
        sys.exit(1)

    except IndexError:
        raise ValueError("Invalid URL format.")

def get_album_id(url):
    """
    Extracts the album ID from the provided URL.

    Args:
        url (str): The URL from which to extract the album ID.

    Returns:
        str: The extracted album ID.

    Raises:
        ValueError: If the URL format is incorrect.
    """
    try:
        return url.split('/')[-1]
    except IndexError:
        raise ValueError("Invalid URL format.")

def fetch_page(url):
    """
    Fetches the HTML content of a page at the given URL.

    Args:
        url (str): The URL to fetch.

    Returns:
        BeautifulSoup: Parsed HTML content of the page.

    Raises:
        requests.RequestException: If there are issues with the request.
    """
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()

        if response.status_code == 500:
            print(
                f"\t\t[-] Internal server error when fetching {url}, "
                + "check the log file"
            )
            write_on_session_log(url)
            sys.exit(1)

        elif response.status_code == 403:
            print(
                f"\t\t[-] DDoSGuard blocked the request to {url}, "
                + "check the log file"
            )
            write_on_session_log(url)
            sys.exit(1)

        return BeautifulSoup(response.text, 'html.parser')

    except requests.RequestException as req_err:
        print(f"\t\t[-] Error: {req_err}")
        return None

async def run(url):
    """
    Initiates the download process for the specified URL using Playwright.

    Args:
        url (str): The URL of the media to download.

    Returns:
        str or None: The download link if successful, or None if an error
                     occurs.
    """
    print(f"\t\t[+] Trying to download with Playwright...")
    item_type = get_item_type(url)

    # If the item is a video or a non-picture file, it can be downloaded
    # through this online app. Note that, in the case of the file, the item tag
    # 'd' is replaced by 'v' when validating the item page URL
    if item_type == 'v':
        return await extract_media_download_link(url, 'video')

    # The only other item type is picture, which can be downloaded through this
    # online app
    return await extract_media_download_link(url, 'picture')

def get_download_path(url):
    """
    Determines the path to save downloaded media based on the URL type.

    Args:
        url (str): The URL to check.

    Returns:
        str: The download path.
    """
    is_album = check_url_type(url)

    if is_album:
        album_id = get_album_id(url)
        return os.path.join(DOWNLOAD_FOLDER, album_id)

    return DOWNLOAD_FOLDER

def create_download_directory(download_path):
    """
    Creates the download directory if it does not already exist.

    Args:
        download_path (str): The path of the directory to create.

    Raises:
        SystemExit: If there is an error creating the directory.
    """
    try:
        os.makedirs(download_path, exist_ok=True)
    except OSError as os_err:
        print(f"\t\t[-] Error creating directory: {os_err}")
        sys.exit(1)

def progress_bar():
    """
    Creates and returns a progress bar for tracking download progress.

    Returns:
        Progress: A Progress object configured with relevant columns.
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        "-",
        TransferSpeedColumn(),
        "-",
        TimeRemainingColumn(),
        transient=True
    )

async def download(download_link, download_path, file_name):
    """
    Downloads a file from the given download link to the specified path.

    Args:
        download_link (str): The URL to download the file from.
        download_path (str): The directory to save the downloaded file.
        file_name (str): The name to save the file as.

    Raises:
        requests.RequestException: If there are issues during the download.
    """
    try:
        response = requests.get(download_link, stream=True, headers=HEADERS)
        response.raise_for_status()

        final_path = os.path.join(download_path, file_name)
        file_size = int(response.headers.get('content-length', -1))

        with open(final_path, 'wb') as file:
            with progress_bar() as pbar:
                task = pbar.add_task("[cyan]Progress", total=file_size)

                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        file.write(chunk)
                        pbar.update(task, advance=len(chunk))

    except requests.RequestException as req_err:
        print(f"\t\t[-] Error during download: {req_err}")
    except IOError as io_err:
        print(f"\t\t[-] File error: {io_err}")

def print_status_message(url):
    """
    Prints a message indicating the start of the download process.

    Args:
        url (str): The URL of the media to download.
    """
    try:
        is_album = check_url_type(url)
        identifier = get_album_id(url) if is_album else url.split('/')[-1]
        message_type = "Album" if is_album else "File"

        print(
            f"\nDownloading {message_type}: "
            + f"{COLORS['BOLD']}{identifier}{COLORS['END']}"
        )

    except IndexError as indx_err:
        print(f"\t\t[-] Error extracting the identifier: {indx_err}")

def print_completion_message():
    """
    Prints a message indicating that the download is complete.
    """
    print("\t[\u2713] Download complete.")

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
    except AttributeError as attr_err:
        print(f"\t\t[-] Error extracting source: {attr_err}")
    except UnboundLocalError as unb_err:
        print(f"\t\t[-] Error extracting item container: {unb_err}")

def get_item_type(item_page):
    """
    Extracts the type of item (album or single file) from the item page URL.

    Args:
        item_page (str): The item page URL.

    Returns:
        str: The type of item ('v' or 'd').

    Raises:
        AttributeError: If there is an error extracting the item type.
    """
    try:
        item_type = item_page.split('/')[-2]
        return item_type

    except AttributeError as attr_err:
        print(f"\t\t[-] Error extracting the item type: {attr_err}")

def validate_item_page(item_page):
    """
    Validates and adjusts the item page URL if necessary.

    Args:
        item_page (str): The item page URL.

    Returns:
        str: The validated item page URL.
    """
    item_type = get_item_type(item_page)

    if item_type == 'd':
        return item_page.replace('/d/', '/v/')

    return item_page

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
        item_download_link = await run(validated_item_page)

    else:
        item_type = get_item_type(validated_item_page)
        item_download_link = get_item_download_link(item_soup, item_type)

    try:
        item_file_name = item_download_link.split('/')[-1] \
            if item_download_link else None
    except IndexError as indx_err:
        print(f"\t\t[-] Error while extracting the file name: {indx_err}")

    return item_download_link, item_file_name

async def download_album(item_pages, download_path):
    """
    Downloads all items in an album from a list of item pages.

    Args:
        item_pages (list): A list of item page URLs.
        download_path (str): The path to save the downloaded files.

    Raises:
        TypeError: If there is an error during the download process.
    """
    try:
        for item_page in item_pages:
            validated_item_page = validate_item_page(item_page)
            item_soup = fetch_page(validated_item_page)
            (item_download_link, item_file_name) = await get_download_info(
                item_soup, validated_item_page
            )

            if not item_download_link:
                print(f"\t\t[-] No download link found for {item_page}")
                continue

            print(f"\t[+] Downloading {item_file_name}...")
            await download(item_download_link, download_path, item_file_name)

    except TypeError as type_err:
        print(f"\t\t[-] Error downloading album: {type_err}")

async def handle_download_process(soup, url, download_path):
    """
    Handles the download process for a given URL, determining if it's an album
    or a single file.

    Args:
        soup (BeautifulSoup): Parsed HTML content of the main page.
        url (str): The URL of the media to download.
        download_path (str): The path to save the downloaded files.
    """
    is_album = check_url_type(url)

    if is_album:
        item_pages = extract_item_pages(soup)
        await download_album(item_pages, download_path)
    else:
        (download_link, file_name) = await get_download_info(soup, url)
        await download(download_link, download_path, file_name)

async def main():
    """
    Main entry point of the script, orchestrating the download process.

    Ensures the correct usage of the script and manages the overall flow of
    downloading media.
    """
    if len(sys.argv) != 2:
        print(f"Usage: python3 {SCRIPT_NAME} <album_url>")
        sys.exit(1)

    url = sys.argv[1]
    print_status_message(url)
    soup = fetch_page(url)

    try:
        download_path = get_download_path(url)
        create_download_directory(download_path)
        await handle_download_process(soup, url, download_path)

    except ValueError as val_err:
        print(f"\t\t[-] Value error: {val_err}")

    finally:
        print_completion_message()

if __name__ == '__main__':
    asyncio.run(main())
