"""
A module for downloading single media (images and videos) from Bunkr URLs
using Playwright for browser automation. It supports two types of downloads:
pictures and videos. The module handles navigating to the media site,
inputting the media URL, and extracting the download link.
"""

import re
import time
from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError
)

SESSION_LOG = 'session_log.txt'
TIMEOUT = 5000

# https://goonlinetools.com/online-image-downloader/
CONFIG = {
    'url': "https://9xbuddy.in/en",
    'input_selector': "input.w-full",
    'button_selector': r".w-8\/12",
    'download_button': (
        r"div.lg\:flex:nth-child(6) > div:nth-child(2) > a:nth-child(1)"
    ),
    'attribute': "href"
}

def wait_and_extract_download_link(
        page, download_button_selector, attribute
):
    """
    Waits for a download link to become available on the page, then extracts
    and returns its attribute.

    Args:
        page: The Playwright page object.
        download_button_selector (str): The CSS selector for the download
                                        button.
        timeout (int): The maximum time to wait for the selector.
        attribute (str): The attribute to retrieve from the
                         element (e.g., 'src', 'href').

    Returns:
        str or None: The value of the specified attribute, or None if the
                     element is not found.
    """
    page.wait_for_selector(download_button_selector, timeout=TIMEOUT)
    element = page.query_selector(download_button_selector)
    return element.get_attribute(attribute) if element else None

def write_on_session_log(url):
    """
    Appends a URL to the session log file.

    Args:
        url (str): The URL to log.
    """
    with open(SESSION_LOG, 'a', encoding='utf-8') as file:
        file.write(f"{url}\n")

#def log_ddos_blocked_request(download_link, url):
#    """
#    Logs requests blocked by DDoSGuard.

#    Args:
#        download_link (str): The link being checked for DDoSGuard blocks.
#        url (str): The original URL that was requested.
#    """
#    if "cloudfl" in download_link:
#        print(
#            f"DDoSGuard blocked the request to {url}, check the log file"
#        )
#        write_on_session_log(url)

def run(playwright, url):
    """
    Main function to execute the download process using Playwright.

    Args:
        playwright: The Playwright instance.
        url (str): The URL of the media to download.

    Returns:
        str or None: The download link if successful, or None if an error
                     occurs.
    """
    # Set headless to False to see the browser
    browser = playwright.firefox.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        page.goto(CONFIG['url'])
        page.fill(CONFIG['input_selector'], url)
        page.wait_for_selector(CONFIG['button_selector'], timeout=TIMEOUT)
        page.click(CONFIG['button_selector'])

        download_link = wait_and_extract_download_link(
            page,
            CONFIG['download_button'],
            CONFIG['attribute']
        )

#        log_ddos_blocked_request(download_link, CONFIG['url'])
        return download_link

    except PlaywrightTimeoutError:
        print(
            "\t[#] This page has no download link or temporarily blocked, "
            "check the log file"
        )
        write_on_session_log(url)
        return None

    finally:
        page.close()
        context.close()
        browser.close()

    return None

def clean_filename(filename):
    """
    Cleans the given filename by removing unwanted parts and replacing
    the last underscore before the extension with a dot.

    Args:
        filename (str): The original filename to clean.

    Returns:
        str: The cleaned filename with the appropriate extension.
    """
    # Regular expression to find the pattern before the last part
    match = re.match(r'^(.*?)(_.*?)(?:\+%7C.+)?$', filename)
    if match:
        base = match.group(1)
        extension = match.group(2).replace('_', '')
        return f"{base}.{extension}"

    return filename

def extract_media_download_link(url, item_type, retries=3):
    """
    Extracts the download link for the specified media type.

    Args:
        url (str): The URL of the media to download.
        item_type (str): The type of item to download ('picture' or 'video').

    Returns:
        str or None: The download link if successful, or None if an error
                     occurs.
    """
    url = url.replace('/i/', '/v/') if item_type == 'picture' else url

    with sync_playwright() as playwright:
        for attempt in range(retries):
            try:
                download_link = run(playwright, url)
                if download_link:
                    filename = download_link.split('customName=')[-1]
                    filename = clean_filename(filename)
                    return (filename, download_link)

            except PlaywrightTimeoutError:
                if attempt < retries - 1:
                    time.sleep(1)

    return None, None

def main():
    """
    Tests the media download link extraction for both picture and video URLs.
    """
    picture_url = "https://bunkr.fi/i/YddngfgJd0cna"
    print(f"\nDownloading from picture URL: {picture_url}")
    download_info = extract_media_download_link(picture_url, 'picture')
    print(f"Download info: {download_info}")

    video_url = "https://bunkr.fi/v/5EpJtKRGzLXfd"
    print(f"\nDownloading from video URL: {video_url}")
    download_info = extract_media_download_link(video_url, 'video')
    print(f"Download link: {download_info}")

if __name__ == '__main__':
    main()
