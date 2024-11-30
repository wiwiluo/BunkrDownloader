"""
A module for downloading single media (images and videos) from Bunkr URLs
using Playwright for browser automation. It supports two types of downloads:
pictures and videos. The module handles navigating to the media site,
inputting the media URL, and extracting the download link.
"""

import re
import random
import asyncio

from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError
)

from .file_utils import write_on_session_log

SESSION_LOG = 'session_log.txt'
TIMEOUT = 5000

CONFIG = {
    'url': "https://9xbuddy.in/en",
    'input_selector': "input.w-full",
    'button_selector': r".w-8\/12",
    'download_button': (
        r"div.lg\:flex:nth-child(6) > div:nth-child(2) > a:nth-child(1)"
    ),
    'attribute': "href"
}

async def wait_and_extract_download_link(
        page, download_button_selector, attribute
):
    """
    Waits for a download link to become available on the page, then extracts
    and returns its attribute.

    Args:
        page: The Playwright page object.
        download_button_selector (str): The CSS selector for the download
                                        button.
        attribute (str): The attribute to retrieve from the
                         element (e.g., 'src', 'href').

    Returns:
        str or None: The value of the specified attribute, or None if the
                     element is not found.
    """
    await page.wait_for_selector(download_button_selector, timeout=TIMEOUT)
    element = await page.query_selector(download_button_selector)
    return await element.get_attribute(attribute) if element else None

async def run(playwright, url):
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
    browser = await playwright.firefox.launch(headless=True)
    context = await browser.new_context()
    page = await context.new_page()

    try:
        await page.goto(CONFIG['url'])
        await page.fill(CONFIG['input_selector'], url)
        await page.wait_for_selector(CONFIG['button_selector'], timeout=TIMEOUT)
        await page.click(CONFIG['button_selector'])

        download_link = await wait_and_extract_download_link(
            page,
            CONFIG['download_button'],
            CONFIG['attribute']
        )
        return download_link

    except PlaywrightTimeoutError:
        print(
            "This page has no download link or temporarily blocked, "
            "check the log file"
        )
        write_on_session_log(url)
        return None

    finally:
        await page.close()
        await context.close()
        await browser.close()

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
    match = re.match(r'^(.*?)(_.*?)(?:\+%7C.+)?$', filename)
    if match:
        base = match.group(1)
        extension = match.group(2).replace('_', '')
        return f"{base}.{extension}"

    return filename

async def extract_media_download_link(url, item_type, retries=3):
    """
    Extracts the download link for a specific media item (either a picture or a
    video) from the given URL using Playwright. The function handles retries in
    case of failures.

    Args:
        url (str): The URL of the media page to extract the download link from.
        item_type (str): The type of media to download. Should be either
                         'picture' or 'video'.
        retries (int): The number of attempts to retry in case of failures
                       (default is 3).

    Returns:
        tuple: A tuple containing:
            - filename (str): The cleaned filename derived from the download
                              link.
            - download_link (str): The extracted download link for the media.

    Raises:
        PlaywrightTimeoutError: If Playwright encounters a timeout error during
                                execution.
    """
    validated_url = (
        url.replace('/i/', '/v/') if item_type == 'picture' else url
    )

    async with async_playwright() as playwright:
        for attempt in range(retries):
            try:
                download_link = await run(playwright, validated_url)
                if download_link:
                    filename = clean_filename(
                        download_link.split("customName=")[-1]
                    )
                    return download_link, filename

                print(
                    "No download link found through Playwright... "
                    f"({attempt + 1}/{retries})"
                )

            except PlaywrightTimeoutError:
                print("Playwright timed out... ({attempt + 1}/{retries})")
                if attempt < retries - 1:
                    delay = 2 ** (attempt + 1) + random.uniform(0, 1)
                    await asyncio.sleep(delay)

    # This block executes if the loop completes without returning a result
    return None, None

async def main():
    """
    Tests the media download link extraction for both picture and video URLs.
    """
    async def test_module(url, media_type):
        print(f"\nExtracting download info from URL: {url}")
        download_link, filename = await extract_media_download_link(
            url, media_type
        )
        print(
            f"Download link: {download_link}\n"
            f"File name: {filename}"
        )

    picture_url = "https://bunkr.fi/i/YddngfgJd0cna"
    await test_module(picture_url, 'picture')

    video_url = "https://bunkr.fi/v/5EpJtKRGzLXfd"
    await test_module(video_url, 'video')

if __name__ == '__main__':
    asyncio.run(main())
