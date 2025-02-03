"""
The `media_downloader` module provides tools to manage the downloading of
individual files, particularly from Bunkr URLs. It supports retry mechanisms,
progress tracking, and error handling for a robust download experience.
"""

import os
import time
import random

import requests

from helpers.config import DOWNLOAD_HEADERS as HEADERS
from helpers.file_utils import write_on_session_log
from helpers.bunkr_utils import (
    subdomain_is_offline,
    mark_subdomain_as_offline
)

from .download_utils import save_file_with_progress

class MediaDownloader:
    """
    Manages the downloading of individual files from Bunkr URLs, providing 
    support for retries, progress updates, and error handling.

    Attributes:
        bunkr_status (dict): Tracks the status of Bunkr subdomains to identify
                             operational issues.
        download_path (str): Directory path where downloaded files will be
                             saved.
        download_link (str): The URL of the file to be downloaded.
        file_name (str): The name of the file being downloaded.
        task (str): Task ID used to track and update download progress.
        live_manager (LiveManager): Facilitates live display of download
                                    progress and logging.
        retries (int): Maximum number of retry attempts for download failures.
    """

    def __init__(
        self, session_info, download_info, live_manager,
        retries=5,
        args=None
    ):
        self.bunkr_status, self.download_path = session_info
        self.download_link, self.file_name, self.task = download_info
        self.live_manager = live_manager
        self.retries = retries
        self.args = args

    def handle_request_exception(self, req_err, attempt):
        """Handles exceptions during the request and manages retries."""
        if req_err.response is None:
            # Mark the subdomain as offline and exit the loop
            marked_subdomain = mark_subdomain_as_offline(
                self.bunkr_status, self.download_link
            )
            self.live_manager.update_log(
                "No response",
                f"Subdomain {marked_subdomain} has been marked as offline."
            )
            return False

        if req_err.response.status_code == 429:
            self.live_manager.update_log(
                "Too many requests",
                f"Retrying to download {self.file_name}... "
                f"({attempt + 1}/{self.retries})"
            )
            if attempt < self.retries - 1:
                # Retry the request
                delay = 4 ** (attempt + 1) + random.uniform(2, 4)
                time.sleep(delay)
                return True

        # Do not retry, exit the loop
        return False

    def skip_file_download(self, final_path):
        """
        Check if the file exists or is in the ignore list, or is not in the
        include list. If so, skip the download.
        """
        def log_and_skip(reason):
            self.live_manager.update_log("Skipped download", reason)
            self.live_manager.update_task(
                self.task,
                completed=100,
                visible=False
            )
            return True

        ignore_list = getattr(self.args, 'ignore', [])
        include_list = getattr(self.args, 'include', [])

        # Check if the file already exists
        if os.path.exists(final_path):
            return log_and_skip(f"{self.file_name} already exists.")

        # Check if the file is in the ignore list (if specified)
        if ignore_list:
            is_in_ignore = any(word in self.file_name for word in ignore_list)
            if is_in_ignore:
                return log_and_skip(
                    f"{self.file_name} contains ignored words."
                )

        # Check if the file is not in the include list (if specified)
        if include_list:
            not_in_include = all(
                word not in self.file_name
                for word in include_list
            )
            if not_in_include:
                return log_and_skip(
                    f"{self.file_name} does not contain required words."
                )

        # If none of the skip conditions are met, return False (do not skip)
        return False

    def attempt_download(self, final_path):
        """Attempt to download the file with retries."""
        for attempt in range(self.retries):
            try:
                response = requests.get(
                    self.download_link,
                    stream=True,
                    headers=HEADERS,
                    timeout=30
                )
                response.raise_for_status()

                # Exit the loop if the download is successful
                save_file_with_progress(
                    response, final_path, self.task, self.live_manager
                )
                return False

            except requests.RequestException as req_err:
                # Exit the loop if not retrying
                if not self.handle_request_exception(req_err, attempt):
                    break

        return True

    def handle_failed_download(self, retry_failed):
        """Handle a failed download after all retry attempts."""
        if not retry_failed:
            self.live_manager.update_log(
                "Exceeded retry attempts",
                f"Exceeded retry attempts for {self.file_name}. "
                "It will be retried one more time after all other tasks."
            )
            return {
                'id': self.task,
                'file_name': self.file_name,
                'download_link': self.download_link
            }

        self.live_manager.update_log(
            "Download failed",
            f"Failed to download {self.file_name}. "
            "The failure has been logged."
        )
        self.live_manager.update_task(self.task, visible=False)
        return None

    def download(self):
        """Main method to handle the download process."""
        retry_failed = self.retries == 1
        is_offline = subdomain_is_offline(
            self.download_link,
            self.bunkr_status
        )

        if is_offline and retry_failed:
            self.live_manager.update_log(
                "Non-operational subdomain",
                f"The subdomain for {self.file_name} appears to be offline. "
                "Check the log file."
            )
            write_on_session_log(self.download_link)
            self.live_manager.update_task(self.task, visible=False)
            return None

        final_path = os.path.join(self.download_path, self.file_name)

        # Skip download if the file exists or is blacklisted
        if self.skip_file_download(final_path):
            return None

        # Attempt to download the file with retries
        failed_download = self.attempt_download(final_path)

        # Handle failed download after retries
        if failed_download:
            return self.handle_failed_download(retry_failed)

        return None
