"""Utilities for fetching pages, managing directories, and clearing the terminal.

It includes functions to handle common tasks such as sending HTTP requests,
parsing HTML, creating download directories, and clearing the terminal, making it
reusable across projects.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import re
import sys
from http.client import RemoteDisconnected
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests import Response

from .config import DOWNLOAD_FOLDER, DOWNLOAD_HEADERS, HTTP_STATUS_SERVER_DOWN
from .file_utils import write_on_session_log


def validate_download_link(download_link: str) -> bool:
    """Check if a download link is accessible."""
    try:
        response = requests.head(download_link, headers=DOWNLOAD_HEADERS, timeout=5)

    except requests.RequestException:
        return False

    return response.status_code != HTTP_STATUS_SERVER_DOWN


async def fetch_page(url: str, retries: int = 5) -> BeautifulSoup | None:
    """Fetch the HTML content of a page at the given URL, with retry logic."""
    error_messages = {
        500: f"Internal server error when fetching {url}",
        502: f"Bad gateway for {url}, probably offline",
        403: f"DDoSGuard blocked the request to {url}",
    }

    def handle_response(response: Response) -> BeautifulSoup | None:
        """Process the HTTP response and handles specific status codes."""
        if response.status_code in error_messages:
            log_message = f"{error_messages[response.status_code]}, check the log file"
            logging.exception(log_message)
            write_on_session_log(url)
            return None

        return BeautifulSoup(response.text, "html.parser")

    for attempt in range(retries):
        try:
            response = requests.Session().get(url, timeout=40)
            response.raise_for_status()
            return handle_response(response)

        except RemoteDisconnected:
            logging.exception("Remote end closed connection without response.")
            if attempt < retries - 1:
                # Add jitter to avoid a retry storm
                delay = 2 ** (attempt + 1) + random.uniform(1, 2)  # noqa: S311
                asyncio.sleep(delay)

        except requests.RequestException as req_err:
            log_message = f"Request error for {url}: {req_err}"
            logging.exception(log_message)
            return None

    return None


def format_directory_name(directory_name: str, directory_id: int | None) -> str | None:
    """Format a directory name by appending its ID in parentheses if the ID is provided.

    If the directory ID is `None`, only the directory name is returned.
    """
    if directory_name is None:
        return directory_id

    return f"{directory_name} ({directory_id})" if directory_id is not None else None


def sanitize_directory_name(directory_name: str) -> str:
    """Sanitize a given directory name by replacing invalid characters with underscores.

    Handles the invalid characters specific to Windows, macOS, and Linux.
    """
    invalid_chars_dict = {
        "nt": r'[\\/:*?"<>|]',  # Windows
        "posix": r"[/:]",       # macOS and Linux
    }
    invalid_chars = invalid_chars_dict.get(os.name)
    return re.sub(invalid_chars, "_", directory_name)


def create_download_directory(directory_name: str) -> str:
    """Create a directory for downloads if it doesn't exist."""
    download_path = (
        Path(DOWNLOAD_FOLDER) / sanitize_directory_name(directory_name)
        if directory_name
        else Path(DOWNLOAD_FOLDER)
    )

    try:
        download_path.mkdir(parents=True, exist_ok=True)
        return str(download_path)

    except OSError:
        logging.exception("Error creating 'Downloads' directory.")
        sys.exit(1)


def clear_terminal() -> None:
    """Clear the terminal screen based on the operating system."""
    commands = {
        "nt": "cls",       # Windows
        "posix": "clear",  # macOS and Linux
    }

    command = commands.get(os.name)
    if command:
        os.system(command)  # noqa: S605
