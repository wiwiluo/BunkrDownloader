"""
Module for extracting media download links from item pages.
"""

from helpers.general_utils import fetch_page

def extract_item_pages(soup, host_page):
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

        if not items:
            print("No item pages found in the HTML content.")

        return [f"{host_page}{item.get('href')}" for item in items]

    except AttributeError as attr_err:
        print(f"Error extracting item pages: {attr_err}")

    return []

def get_item_container(item_soup):
    """
    Extracts the first available image or source container from the provided
    BeautifulSoup object.

    Args:
        item_soup (BeautifulSoup): A BeautifulSoup object representing the HTML
                                   structure of the item.

    Returns:
        BeautifulSoup element or None: The first found <source> or <img>
        element with a 'src' attribute, or None if neither is found.
    """
    # Try to find the <source> element
    item_container = item_soup.find('source', {'src': True})

    # If no <source> element is found, try to find an <img> element
    if item_container is None:
        item_container = item_soup.find(
            'img', 
            {
                'class': "max-h-full w-auto object-cover relative z-20",
                'src': True
            }
        )

    # Return the found element (either <source>, <img>, or None if neither was
    # found)
    return item_container

async def get_non_media_download_link(item_soup):
    """
    Extracts the download link for a non-media item from a provided
    BeautifulSoup object.

    Args:
        item_soup (BeautifulSoup): A BeautifulSoup object representing the HTML
                                   structure of the item page containing the
                                   first download link.

    Returns:
        str: The download link (URL) of the non-media item extracted from the
             second page.
    
    Raises:
        AttributeError: If the necessary download link or buttons are not found
                        on the pages.
        Exception: If there is any issue during fetching or parsing the pages.
    """
    # Find the first download button in the initial page
    non_media_container = item_soup.find(
        'a',
        {
            'class': (
                "btn btn-main btn-lg rounded-full px-6 font-semibold flex-1 "
                "ic-download-01 ic-before before:text-lg"
            ),
            'href': True
        }
    )

    # Fetch the page linked from the first download button
    non_media_item_soup = await fetch_page(non_media_container['href'])

    # Find the second download button in the fetched page
    non_media_download_container = non_media_item_soup.find(
        'a',
        {
            'class': (
                "btn btn-main btn-lg rounded-full px-6 font-semibold "
                "ic-download-01 ic-before before:text-lg"
            ),
            'href': True
        }
    )

    # Return the download link extraced from the 'href' attribute
    return non_media_download_container['href']

async def get_item_download_link(item_soup):
    """
    Retrieves the download link for a specific item from its HTML content.

    Args:
        item_soup (BeautifulSoup): The BeautifulSoup object representing the
                                   parsed HTML content of the item.

    Returns:
        str: The download link (URL) for the item. Returns `None` if the link
             cannot be found.

    Raises:
        AttributeError: If the required `src` attribute is not found for the
                        specified `item_type`.
    """
    item_container = get_item_container(item_soup)

    if item_container is None:
        return await get_non_media_download_link(item_soup)

    try:
        return item_container['src']

    except AttributeError as err:
        print(f"Error extracting source: {err}")

    return None

def get_item_filename(item_soup):
    """
    Extracts the filename from the provided HTML soup.

    Args:
        item_soup (BeautifulSoup): The parsed HTML content containing the item
                                   information.

    Returns:
        str: The extracted filename text.
    """
    filename_container = item_soup.find(
        'h1',
        {'class': "text-subs font-semibold text-base sm:text-lg truncate"}
    )
    return filename_container.get_text()

async def get_download_info(item_soup):
    """
    Gathers download information (link and filename) for the item.

    Args:
        item_soup (BeautifulSoup): Parsed HTML content of the item.

    Returns:
        tuple: A tuple containing the download link and file name.
    """
    item_download_link = await get_item_download_link(item_soup)

    item_file_name = (
        get_item_filename(item_soup) if item_download_link
        else None
    )
    return item_download_link, item_file_name
