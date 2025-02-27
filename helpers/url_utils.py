"""Module to analyze and extract details from URLs related to albums and video files.

The primary focus is on distinguishing between album URLs and individual file URLs, and
extracting relevant identifiers for albums or videos.
"""

from __future__ import annotations

import html
import logging
import sys
from base64 import b64decode
from math import floor
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import requests

from .config import BUNKR_API, HTTP_STATUS_OK

if TYPE_CHECKING:
    from bs4 import BeautifulSoup


def get_host_page(url: str) -> str:
    """Extract the base host URL from a given URL."""
    url_netloc = urlparse(url).netloc
    return f"https://{url_netloc}"


def check_url_type(url: str) -> bool:
    """Determine whether the provided URL corresponds to an album or a single file."""
    url_mapping = {"a": True, "f": False, "v": False}

    try:
        url_segment = url.split("/")[-2]

        if url_segment in url_mapping:
            return url_mapping[url_segment]

        logging.exception("Enter a valid album or file URL.")

    except IndexError:
        logging.exception("Invalid URL format.")

    return None


def get_identifier(url: str) -> str:
    """Extract the identifier from the provided URL.

    This function determines if the given URL corresponds to an album. If it is,
    it returns the album ID. If not, it returns the last part of the URL (usually
    the individual item identifier).
    """
    try:
        is_album = check_url_type(url)
        return get_album_id(url) if is_album else url.split("/")[-1]

    except IndexError:
        logging.exception("Error extracting the identifier.")

    return url


def get_album_id(url: str) -> str:
    """Extract the album or video ID from the provided URL."""
    try:
        return url.split("/")[-1]

    except IndexError:
        logging.exception("Invalid URL format.")
        sys.exit(1)


def get_album_name(soup: BeautifulSoup) -> str | None:
    """Extract the album name from the HTML of a page.

    If the album name cannot be found, a message is printed, and `None` is returned.
    """
    name_container = soup.find(
        "div",
        {"class": "text-subs font-semibold flex text-base sm:text-lg"},
    )

    if name_container:
        album_name = name_container.find("h1").get_text(strip=True)
        return html.unescape(album_name)

    return None


def get_item_type(item_page: str) -> str:
    """Extract the type of item (album or single file) from the item page URL."""
    try:
        return item_page.split("/")[-2]

    except AttributeError:
        logging.exception("Error extracting the item type.")

    return None


def get_url_based_filename(item_download_link: str) -> str:
    """Extract the filename from a download link by removing any directory structure."""
    parsed_url = urlparse(item_download_link)
    # The download link path contains the filename, preceded by a '/'
    return parsed_url.path.split("/")[-1]


def get_api_response(slug: str) -> dict | None:
    """Fetch encryption data for a given slug from the Bunkr API."""
    try:
        with requests.Session() as session:
            response = session.post(BUNKR_API, json={"slug": slug})

            if response.status_code != HTTP_STATUS_OK:
                log_message = (
                    f"Failed to fetch encryption data for slug '{slug}' "
                    f"(status: {response.status_code})"
                )
                logging.warning(log_message)
                return None

        return response.json()

    except requests.RequestException as req_err:
        log_message = (
            f"Error while requesting encryption data for slug '{slug}': {req_err}"
        )
        logging.exception(log_message)
        return None


def decrypt_url(api_response: dict) -> str:
    """Decrypt an encrypted URL using a time-based secret key."""
    try:
        timestamp = api_response["timestamp"]
        encrypted_bytes = b64decode(api_response["url"])

    except KeyError as key_err:
        log_message = f"Missing required encryption data field: {key_err}"
        logging.exception(log_message)

    time_key = floor(timestamp / 3600)
    secret_key = f"SECRET_KEY_{time_key}"
    secret_key_bytes = secret_key.encode("utf-8")

    return "".join(
        chr(byte ^ secret_key_bytes[indx % len(secret_key_bytes)])
        for indx, byte in enumerate(encrypted_bytes)
    )
