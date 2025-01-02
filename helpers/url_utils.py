"""
This module provides functions to analyze and extract details from URLs related
to albums and video files. The primary focus is on distinguishing between album
URLs and individual video file URLs, and extracting relevant identifiers for 
albums or videos.
"""

import sys

def check_url_type(url):
    """
    Determines whether the provided URL corresponds to an album or a single
    video file.

    Args:
        url (str): The URL to check.

    Returns:
        bool: True if the URL is for an album, False if it is for a single
              video file.

    Raises:
        SystemExit: If the URL is invalid.
        ValueError: If the URL format is incorrect.
    """
    try:
        url_segment = url.split('/')[-2]
        url_mapping = {'a': True, 'v': False}

        if url_segment in url_mapping:
            return url_mapping[url_segment]

        print('Enter a valid video or album URL.')
        sys.exit(1)

    except IndexError as indx_err:
        raise ValueError("Invalid URL format.") from indx_err

    return None

def get_identifier(url):
    """
    Extracts individual item pages (URLs) from the parsed HTML content.

    Args:
        soup (BeautifulSoup): The parsed HTML content of the page.

    Returns:
        list: A list of URLs pointing to individual item pages.

    Raises:
        AttributeError: If there is an error accessing the required HTML
                        attributes (e.g., missing or malformed tags).
    """
    try:
        is_album = check_url_type(url)
        return get_album_id(url) if is_album else url.split('/')[-1]

    except IndexError as indx_err:
        print(f"Error extracting the identifier: {indx_err}")

    return url

def get_album_id(url):
    """
    Extracts the album or video ID from the provided URL.

    Args:
        url (str): The URL from which to the ID.

    Returns:
        str: The extracted ID.

    Raises:
        ValueError: If the URL format is incorrect.
    """
    try:
        return url.split('/')[-1]

    except IndexError as indx_err:
        raise ValueError("Invalid URL format.") from indx_err

def get_album_name(soup):
    """
    Extracts the album name from a BeautifulSoup object representing the HTML
    of a page. If the album name cannot be found, a message is printed, and
    `None` is returned.

    Args:
        soup (BeautifulSoup): A BeautifulSoup object containing the HTML of the
                              page.

    Returns:
        str or None: The extracted album name as a string, with any leading/
                     trailing whitespace removed. If the album name is not
                     found, returns `None`.
    """
    name_container = soup.find(
        'div',
        {'class': "text-subs font-semibold flex text-base sm:text-lg"}
    )

    if name_container:
        return name_container.find('h1').get_text(strip=True)

#    print(
#        "Album name container not found; "
#        "only the Album ID will be used for the directory name."
#    )
    return None

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
        return item_page.split('/')[-2]

    except AttributeError as attr_err:
        print(f"Error extracting the item type: {attr_err}")

    return None

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
