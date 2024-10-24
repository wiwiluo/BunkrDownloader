"""
This module provides functionality to read URLs from a specified file,
validate them, and download the associated content. It manages the entire
download process by leveraging asynchronous operations, allowing for
efficient handling of multiple URLs.

Key Features:
    - Reads a list of URLs from a text file.
    - Validates each URL and downloads content asynchronously.
    - Maintains a session log for tracking download status.
    - Cleans up the URLs file and session log upon completion.

Functions:
    - read_file(filename): Reads the contents of a specified file and returns a
                           list of its lines.
    - write_file(filename, content=''): Writes content to a specified file,
                                        clearing the file if no content is
                                        provided.
    - process_urls(urls): Validates and downloads content for a list of URLs.
    - main(): Main entry point for executing the script, orchestrating the
              overall flow.

Usage:
To run the module, execute the script directly. It will process URLs
listed in 'URLs.txt' and log the session activities in 'session_log.txt'.
"""

import asyncio
from helpers.downloader import validate_and_download

FILE = 'URLs.txt'
SESSION_LOG = 'session_log.txt'

def read_file(filename):
    """
    Reads the contents of a file and returns a list of its lines.

    Args:
        filename (str): The path to the file to be read.

    Returns:
        list: A list of lines from the file, with newline characters removed.
    """
    with open(filename, 'r', encoding='utf-8') as file:
        return file.read().splitlines()

def write_file(filename, content=''):
    """
    Writes content to a specified file. If content is not provided, the file is
    cleared.

    Args:
        filename (str): The path to the file to be written to.
        content (str, optional): The content to write to the file. Defaults to
                                 an empty string.
    """
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(content)

async def process_urls(urls):
    """
    Validates and downloads items for a list of URLs.

    Args:
        urls (list): A list of URLs to process.
    """
    for url in urls:
        await validate_and_download(url)

async def main():
    """
    Main function to execute the script.

    Clears the session log, reads URLs from a file, processes them,
    and clears the URLs file at the end.
    """
    write_file(SESSION_LOG)

    urls = read_file(FILE)
    await process_urls(urls)

    write_file(FILE)

if __name__ == '__main__':
    asyncio.run(main())
