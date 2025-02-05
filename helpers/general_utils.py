"""
This module provides utilities for fetching web pages, managing directories, 
and clearing the terminal screen. It includes functions to handle common tasks 
such as sending HTTP requests, parsing HTML, creating download directories, and
clearing the terminal, making it reusable across projects.
"""

import os
import re
import sys
import random
import asyncio
from http.client import RemoteDisconnected

import requests
from bs4 import BeautifulSoup

from .file_utils import write_on_session_log
from .config import (
    DOWNLOAD_FOLDER,
    DOWNLOAD_HEADERS as HEADERS
)

def validate_download_link(download_link):
    """
    Check if a download link is accessible.

    Args:
        download_link (str): The URL to validate.

    Returns:
        bool: True if the link is accessible, False if blocked (521 status) or
              if a request error occurs.
    """
    try:
        response = requests.head(download_link, headers=HEADERS, timeout=5)
        return response.status_code != 521

    except requests.RequestException as req_err:
        return False

async def fetch_page(url, retries=5):
    """
    Fetches the HTML content of a page at the given URL, with retry logic and
    exponential backoff.

    Args:
        url (str): The URL of the page to fetch. This should be a valid URL 
                   pointing to a webpage.
        retries (int, optional): The number of retry attempts in case of
                                 failure (default is 5).

    Returns:
        BeautifulSoup: A BeautifulSoup object containing the parsed HTML
                       content of the page.

    Raises:
        requests.RequestException: If there are issues with the HTTP request,
                                   such as network problems or invalid URLs.
        RemoteDisconnected: If the remote server closes the connection without
                            sending a response.
    """
    error_messages = {
        500: f"Internal server error when fetching {url}",
        502: f"Bad gateway for {url}, probably offline",
        403: f"DDoSGuard blocked the request to {url}"
    }

    def handle_response(response):
        """Processes the HTTP response and handles specific status codes."""
        if response.status_code in error_messages:
            print(
                f"{error_messages[response.status_code]}, check the log file"
            )
            write_on_session_log(url)
            return None

        return BeautifulSoup(response.text, 'html.parser')

    for attempt in range(retries):
        try:
            response = requests.Session().get(url, timeout=40)
            response.raise_for_status()
            return handle_response(response)

        except RemoteDisconnected:
            print(
                "Remote end closed connection without response. "
                f"Retrying in a moment... ({attempt + 1}/{retries})"
            )
            if attempt < retries - 1:
                # Add jitter to avoid a retry storm
                delay = (2 ** (attempt + 1)) + random.uniform(0, 1)
                asyncio.sleep(delay)

        except requests.RequestException:
#            print(f"Request error for {url}: {req_err}")
            return None

    return None

def format_directory_name(directory_name, directory_id):
    """
    Formats a directory name by appending its ID in parentheses if the ID is
    provided. If the directory ID is `None`, only the directory name is
    returned.

    Args:
        directory_name (str): The name of the directory to format.
        directory_id (int or None): The ID of the directory. If `None`, the
                                    function returns `None`.

    Returns:
        str or None: A formatted string with the directory name followed by
                     the ID in parentheses, or `None` if the `directory_id` is
                     `None`.
    """
    if directory_name is None:
        return directory_id

    return  (
        f"{directory_name} ({directory_id})" if directory_id is not None
        else None
    )

def sanitize_directory_name(directory_name):
    """
    Sanitize a given directory name by replacing invalid characters with
    underscores. Handles the invalid characters specific to Windows, macOS,
    and Linux.

    Args:
        directory_name (str): The original directory name to sanitize.

    Returns:
        str: The sanitized directory name.
    """
    invalid_chars_dict = {
        'nt': r'[\\/:*?"<>|]',  # Windows
        'posix': r'[/:]'        # macOS and Linux
    }
    invalid_chars = invalid_chars_dict.get(os.name)
    return re.sub(invalid_chars, '_', directory_name)

def create_download_directory(directory_name):
    """
    Creates a directory for downloads if it doesn't exist.

    Args:
        directory_name (str): The name used to create the download directory.

    Returns:
        str: The path to the created download directory.

    Raises:
        OSError: If there is an error creating the directory.
    """
    download_path = (
        os.path.join(
            DOWNLOAD_FOLDER,
            sanitize_directory_name(directory_name)
        )
        if directory_name else DOWNLOAD_FOLDER
    )

    try:
        os.makedirs(download_path, exist_ok=True)
        return download_path

    except OSError as os_err:
        print(f"Error creating directory: {os_err}")
        sys.exit(1)

def clear_terminal():
    """
    Clears the terminal screen based on the operating system.
    """
    commands = {
        'nt': 'cls',      # Windows
        'posix': 'clear'  # macOS and Linux
    }

    command = commands.get(os.name)
    if command:
        os.system(command)
