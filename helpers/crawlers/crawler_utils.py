"""
Module for extracting media download links from item pages.

This module contains functions that interact with parsed HTML content to
extract media download links (e.g., videos or images) from item pages. It
utilizes both Playwright for dynamic content extraction and BeautifulSoup for
static content scraping.
"""

from helpers.url_utils import validate_item_page, get_item_type
from .playwright_crawler import extract_media_download_link

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
