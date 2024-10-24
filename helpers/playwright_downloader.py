"""
A module for downloading single media (images and videos) from Bunkr URLs
using Playwright for browser automation. It supports two types of downloads:
pictures and videos. The module handles navigating to the media site,
inputting the media URL, and extracting the download link.

Functions:
- extract_media_download_link(url, item_type): Initiates the download process
                                               for the specified media type.
- test_module(): Tests the functionality of the downloader with sample URLs.

Dependencies:
- asyncio: For asynchronous programming.
- playwright.async_api: For browser automation.

Logging:
- Logs URLs that encounter errors or are blocked in 'session_log.txt'.
"""

import asyncio
from playwright.async_api import async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

SESSION_LOG = 'session_log.txt'

TIMEOUTS = {
    'picture': 25000,
    'video': 5000
}

DOWNLOADER_CONFIGS = {
    'picture': {
        'url': "https://extract.pics/",
        'input_selector': "input.w-full",
        'button_selector': "button.relative",
        'download_button': "div.relative img",
        'attribute': "src"
    },
    'video': {
        'url': "https://9xbuddy.in/en",
        'input_selector': "input.w-full",
        'button_selector': r".w-8\/12",
        'download_button': (
            r"div.lg\:flex:nth-child(4) > div:nth-child(2) > a:nth-child(1)"
        ),
        'attribute': "href"
    }
}

async def wait_and_extract_download_link(
        page, download_button_selector, timeout, attribute
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
    await page.wait_for_selector(download_button_selector, timeout=timeout)
    element = await page.query_selector(download_button_selector)
    return await element.get_attribute(attribute) if element else None

def write_on_session_log(url):
    """
    Appends a URL to the session log file.

    Args:
        url (str): The URL to log.
    """
    with open(SESSION_LOG, 'a') as file:
        file.write(f"{url}\n")

def log_ddos_blocked_request(download_link, url):
    """
    Logs requests blocked by DDoSGuard.

    Args:
        download_link (str): The link being checked for DDoSGuard blocks.
        url (str): The original URL that was requested.
    """
    if "cloudflare" in download_link:
        message = f"DDoSGuard blocked the request to {url}, check the log file."
        print(f"\t\t[#] {message}")
        write_on_session_log(url)

async def run(playwright, url, item_type):
    """
    Main function to execute the download process using Playwright.

    Args:
        playwright: The Playwright instance.
        url (str): The URL of the media to download.
        item_type (str): The type of item to download ('picture' or 'video').

    Returns:
        str or None: The download link if successful, or None if an error
                     occurs.
    """
    config = DOWNLOADER_CONFIGS[item_type]

    # Set headless to False to see the browser
    browser = await playwright.firefox.launch(headless=True)
    context = await browser.new_context()
    page = await context.new_page()

    try:
        await page.goto(config['url'])
        await page.fill(config['input_selector'], url)
        await page.wait_for_selector(config['button_selector'], timeout=5000)
        await page.click(config['button_selector'])

        download_link = await wait_and_extract_download_link(
            page,
            config['download_button'],
            TIMEOUTS[item_type],
            config['attribute']
        )

        log_ddos_blocked_request(download_link, config['url'])
        return download_link

    except PlaywrightTimeoutError:
        message = (
            "This page has no download link or temporarily blocked, "
            "check the log file"
        )
        print(f"\t\t[#] {message}")
        write_on_session_log(url)
        return None

    finally:
        await context.close()
        await browser.close()

    return None

async def extract_media_download_link(url, item_type):
    """
    Extracts the download link for the specified media type.

    Args:
        url (str): The URL of the media to download.
        item_type (str): The type of item to download ('picture' or 'video').

    Returns:
        str or None: The download link if successful, or None if an error
                     occurs.
    """
    async with async_playwright() as playwright:
        download_link = await run(playwright, url, item_type)
        return download_link

async def test_module():
    """
    Tests the media download link extraction for both picture and video URLs.
    """
    picture_url = "https://bunkr.fi/i/YddngfgJd0cna"
    print(f"\nDownloading from picture URL: {picture_url}")
    download_link = await extract_media_download_link(picture_url, 'picture')
    print(f"Download link: {download_link}")

    # This picture triggers the DDoSGuard
    picture_url = "https://bunkr.fi/i/YddngfgJd0cna"
    print(f"\nDownloading from picture URL: {picture_url}")
    download_link = await extract_media_download_link(picture_url, 'picture')
    print(f"Download link: {download_link}")

    video_url = "https://bunkr.fi/v/5EpJtKRGzLXfd"
    print(f"\nDownloading from video URL: {video_url}")
    download_link = await extract_media_download_link(video_url, 'video')
    print(f"Download link: {download_link}")

if __name__ == '__main__':
    asyncio.run(test_module())
