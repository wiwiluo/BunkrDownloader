"""Utilities to fetch the operational status of servers from the Bunkr status page."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .config import HEADERS, STATUS_PAGE


def fetch_page(url: str) -> BeautifulSoup | None:
    """Fetch the HTML content of a page at the given URL."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    except requests.RequestException:
        logging.exception("Error occurred while making the request.")
        return None


def get_bunkr_status() -> dict:
    """Fetch the status of servers from the status page and returns a dictionary."""
    soup = fetch_page(STATUS_PAGE)

    try:
        server_items = soup.find_all(
            "div",
            {
                "class": (
                    "flex items-center gap-4 py-4 border-b border-soft last:border-b-0"
                ),
            },
        )

        bunkr_status = {}
        for server_item in server_items:
            server_name = server_item.find("p").get_text(strip=True)
            server_status = server_item.find("span").get_text(strip=True)
            bunkr_status[server_name] = server_status

    except AttributeError:
        logging.exception("Error extracting server data.")
        return {}

    return bunkr_status


def get_offline_servers(bunkr_status: dict | None = None) -> dict:
    """Return a dictionary of servers that are not operational."""
    bunkr_status = bunkr_status or get_bunkr_status()
    return {
        name: status for name, status in bunkr_status.items() if status != "Operational"
    }


def subdomain_is_offline(download_link: str, bunkr_status: dict | None = None) -> bool:
    """Check if the subdomain from the given download link is marked as offline."""
    offline_servers = get_offline_servers(bunkr_status)

    netloc = urlparse(download_link).netloc
    subdomain = netloc.split(".")[0].capitalize()

    return subdomain in offline_servers


def mark_subdomain_as_offline(bunkr_status: dict, download_link: str) -> str:
    """Mark the subdomain of a given download link as offline in the Bunkr status."""
    netloc = urlparse(download_link).netloc
    subdomain = netloc.split(".")[0].capitalize()
    bunkr_status[subdomain] = "Non-operational"
    return subdomain
