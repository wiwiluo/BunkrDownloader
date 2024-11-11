"""
This module provides functionality to fetch and parse the operational status of
servers from the Bunkr status page.
"""

import sys
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

STATUS_PAGE = "https://status.bunkr.ru/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) "
        "Gecko/20100101 Firefox/117.0"
    )
}

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

        print('\nEnter a valid video or album URL.')
        sys.exit(1)

    except IndexError as indx_err:
        raise ValueError("Invalid URL format.") from indx_err

    return None

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
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')

    except requests.RequestException as req_err:
        print(f"Error: {req_err}")
        return None

def get_bunkr_status():
    """
    Fetches the status of servers from the status page and returns a
    dictionary.

    Returns:
        dict: A dictionary where the keys are server names (str) and the 
              values are their statuses (str). If an error occurs during 
              data extraction, an empty dictionary is returned.
    """
    soup = fetch_page(STATUS_PAGE)

    try:
        server_items = soup.find_all(
            'div',
            {
                'class': (
                    "flex items-center gap-4 py-4 border-b border-soft "
                    "last:border-b-0"
                )
            }
        )

        status_dict = {}
        for server_item in server_items:
            server_name = server_item.find('p').get_text(strip=True)
            server_status = server_item.find('span').get_text(strip=True)
            status_dict[server_name] = server_status

    except AttributeError as attr_err:
        print(f"Error extracting server data: {attr_err}")
        return {}

    return status_dict

def get_non_operational_servers():
    """
    Retrieves a dictionary of non-operational servers.

    Returns:
        dict: A dictionary where the keys are names of non-operational servers
              and the values are their corresponding statuses.
    """
    status_dict = get_bunkr_status()
    return {
        name: status
        for name, status in status_dict.items() if status != "Operational"
    }

def subdomain_is_non_operational(download_link):
    """
    Checks if the subdomain of the given download link is non-operational.

    Args:
        download_link (str): The URL from which the subdomain will be
                             extracted.

    Returns:
        bool: True if the subdomain is non-operational, False otherwise.
    """
    non_operational_servers = get_non_operational_servers()

    netloc = urlparse(download_link).netloc
    subdomain = netloc.split('.')[0].capitalize()

    if subdomain in non_operational_servers:
        return True

    return False

def main():
    """
    Main function to retrieve and print non-operational servers.
    """
    non_operational_servers = get_non_operational_servers()
    print(non_operational_servers)

if __name__ == '__main__':
    main()
