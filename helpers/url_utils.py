"""Module to analyze and extract details from URLs related to albums and video files.

The primary focus is on distinguishing between album URLs and individual file URLs, and
extracting relevant identifiers for albums or videos.
"""

from __future__ import annotations

import html
import logging
import sys
from base64 import b64decode
from itertools import cycle
from math import floor
from typing import TYPE_CHECKING
from urllib.parse import unquote, urlparse, urlunparse

import requests

from .config import BUNKR_API, HTTP_STATUS_OK

if TYPE_CHECKING:
    from bs4 import BeautifulSoup


def get_host_page(url: str) -> str:
    """Extract the base host URL from a given URL."""
    url_netloc = urlparse(url).netloc
    return f"https://{url_netloc}"


def change_domain_to_cr(url: str) -> str:
    """Replace the domain of the given URL with 'bunkr.cr'.

    This is useful for retrying requests using an alternative domain (e.g., when
    the original domain is blocked or returns a 403 error).
    """
    parsed = urlparse(url)
    new_parsed = parsed._replace(netloc="bunkr.cr")
    return urlunparse(new_parsed)


def check_url_type(url: str) -> bool | None:
    """Determine whether the provided URL corresponds to an album or a single file."""
    url_mapping = {"a": True, "f": False, "v": False}

    try:
        url_type = url.split("/")[-2]

    except IndexError:
        logging.exception("Invalid URL format.")

    if url_type in url_mapping:
        return url_mapping[url_type]

    logging.warning("Enter a valid album or file URL.")
    return None


def get_identifier(url: str) -> str:
    """Extract the identifier from the provided URL.

    This function determines if the given URL corresponds to an album. If it is,
    it returns the album ID. If not, it returns the last part of the URL (usually
    the individual item identifier).
    """
    decoded_url = unquote(url)

    try:
        is_album = check_url_type(decoded_url)
        return get_album_id(decoded_url) if is_album else decoded_url.split("/")[-1]

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


def get_item_type(item_page: str) -> str | None:
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


def get_api_response(item_url: str) -> dict[str, bool | str | int] | None:
    """Fetch encryption data for a given slug from the Bunkr API."""
    slug = get_identifier(item_url)

    try:
        with requests.Session() as session:
            response = session.post(BUNKR_API, json={"slug": slug})
            if response.status_code != HTTP_STATUS_OK:
                log_message = f"Failed to fetch encryption data for slug '{slug}'"
                logging.warning(log_message)
                return None

        return response.json()

    except requests.RequestException as req_err:
        log_message = f"Error while requesting encryption data for '{slug}': {req_err}"
        logging.exception(log_message)
        return None


def decrypt_url(api_response: dict[str, bool | str | int]) -> str:
    """Decrypt an encrypted URL using a time-based secret key."""
    try:
        timestamp = api_response["timestamp"]
        encrypted_bytes = b64decode(api_response["url"])

    except KeyError as key_err:
        log_message = f"Missing required encryption data field: {key_err}"
        logging.exception(log_message)
        return ""

    # Generate the secret key based on the timestamp
    time_key = floor(timestamp / 3600)
    secret_key = f"SECRET_KEY_{time_key}"

    # Create a cyclic iterator for the secret key
    secret_key_bytes = secret_key.encode("utf-8")
    cycled_key = cycle(secret_key_bytes)

    # Decrypt the data
    decrypted_bytes = bytearray(byte ^ next(cycled_key) for byte in encrypted_bytes)
    return decrypted_bytes.decode("utf-8", errors="ignore")
