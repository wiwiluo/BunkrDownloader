"""
This module provides functionality to fetch and parse the operational status of
servers from the Bunkr status page.
"""

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

        bunkr_status = {}
        for server_item in server_items:
            server_name = server_item.find('p').get_text(strip=True)
            server_status = server_item.find('span').get_text(strip=True)
            bunkr_status[server_name] = server_status

    except AttributeError as attr_err:
        print(f"Error extracting server data: {attr_err}")
        return {}

    return bunkr_status

def get_offline_servers(bunkr_status=None):
    """
    Returns a dictionary of servers that are not operational.

    Args:
        bunkr_status (dict, optional): A dictionary mapping server names to
                                       their operational status. Defaults to
                                       None.

    Returns:
        dict: A dictionary of servers that are not operational, where the keys
              are server names and the values are their statuses.
    """
    bunkr_status = bunkr_status or get_bunkr_status()
    return {
        name: status
        for name, status in bunkr_status.items() if status != "Operational"
    }

def subdomain_is_offline(download_link, bunkr_status=None):
    """
    Checks if the subdomain from the given download link is marked as offline.

    Args:
        download_link (str): The URL from which the subdomain will be
                             extracted.
        bunkr_status (dict, optional): A dictionary mapping server names to
                                       their operational status.Defaults to
                                       None.

    Returns:
        bool: `True` if the subdomain is offline, otherwise `False`.
    """
    offline_servers = get_offline_servers(bunkr_status)

    netloc = urlparse(download_link).netloc
    subdomain = netloc.split('.')[0].capitalize()

    if subdomain in offline_servers:
        return True

    return False

def mark_subdomain_as_offline(bunkr_status, download_link):
    """
    Marks the subdomain of a given download link as offline in the
    bunkr status.

    Args:
        bunkr_status (dict): A dictionary mapping server names to their
                             operational status.
        download_link (str): The URL from which the subdomain will be
                             extracted.

    Returns:
        str: The name of the subdomain that was marked as offline.
    """
    netloc = urlparse(download_link).netloc
    subdomain = netloc.split('.')[0].capitalize()
    bunkr_status[subdomain] = 'Non-operational'
    return subdomain

def main():
    """
    Main function to retrieve and print non-operational servers.
    """
    offline_servers = get_offline_servers()
    if offline_servers:
        print(f"Offline servers: {offline_servers}")
    else:
        print("All servers are operational.")

    download_link = "https://milkshake.bunkr.ru/-Harem-Camp----08--1080p-UNC--DFpqZR4L.mkv"
    bunkr_status = get_bunkr_status()
    subdomain = mark_subdomain_as_offline(bunkr_status, download_link)
    print(f"Subdomain {subdomain} has been marked as offline.")
    print(f"Updated status: {bunkr_status}")
    print(f"Updated offline servers: {get_offline_servers(bunkr_status)}")
#    print(subdomain_is_offline(download_link, bunkr_status))

if __name__ == '__main__':
    main()
