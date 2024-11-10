"""
This module provides functionality to read URLs from a specified file,
validate them, and download the associated content. It manages the entire
download process by leveraging asynchronous operations, allowing for
efficient handling of multiple URLs.

Usage:
    To run the module, execute the script directly. It will process URLs
    listed in 'URLs.txt' and log the session activities in 'session_log.txt'.
"""

from rich.live import Live

from downloader import validate_and_download, clear_terminal
from helpers.progress_utils import create_progress_bar, create_progress_table

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

def process_urls(urls):
    """
    Validates and downloads items for a list of URLs.

    Args:
        urls (list): A list of URLs to process.
    """
    overall_progress = create_progress_bar()
    job_progress = create_progress_bar()
    progress_table = create_progress_table(overall_progress, job_progress)

    with Live(progress_table, refresh_per_second=10):
        for url in urls:
            validate_and_download(url, job_progress, overall_progress)

def main():
    """
    Main function to execute the script.

    Clears the session log, reads URLs from a file, processes them,
    and clears the URLs file at the end.
    """
    clear_terminal()
    write_file(SESSION_LOG)

    urls = read_file(FILE)
    process_urls(urls)

    write_file(FILE)

if __name__ == '__main__':
    main()
