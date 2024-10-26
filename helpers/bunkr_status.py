"""
This module provides functionality to fetch and parse the operational status of
servers from the Bunkr status page.
"""

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
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')

    except requests.RequestException as req_err:
        print(f"\t\t[-] Error: {req_err}")
        return None

def get_bunkr_status():
    """
    Fetches the status of servers from the status page and returns a dictionary.

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
        print(f"\t[-] Error extracting server data: {attr_err}")
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

def main():
    """
    Main function to retrieve and print non-operational servers.
    """
    non_operational_servers = get_non_operational_servers()
    print(non_operational_servers)

if __name__ == '__main__':
    main()
