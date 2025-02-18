"""Provides tools to manage the downloading of individual files from Bunkr URLs.

It supports retry mechanisms, progress tracking, and error handling for a robust
download experience.
"""

from __future__ import annotations

import random
import time
from pathlib import Path
from typing import TYPE_CHECKING

import requests
from requests import RequestException

from helpers.bunkr_utils import (
    mark_subdomain_as_offline,
    subdomain_is_offline,
)
from helpers.config import DOWNLOAD_HEADERS as HEADERS
from helpers.config import HTTP_STATUS_BAD_GATEWAY, HTTP_STATUS_SERVER_DOWN
from helpers.file_utils import write_on_session_log

from .download_utils import save_file_with_progress

if TYPE_CHECKING:
    from argparse import Namespace

    from BunkrDownloader.helpers.managers.live_manager import LiveManager


class MediaDownloader:
    """Manage the downloading of individual files from Bunkr URLs."""

    def __init__(
        self,
        session_info: tuple,
        download_info: tuple,
        live_manager: LiveManager,
        retries: int = 5,
        args: Namespace | None = None,
    ) -> None:
        """Initialize the MediaDownloader instance."""
        self.bunkr_status, self.download_path = session_info
        self.download_link, self.file_name, self.task = download_info
        self.live_manager = live_manager
        self.retries = retries
        self.args = args

    def skip_file_download(self, final_path: str) -> bool:
        """Determine whether a file should be skipped during download.

        This method checks the following conditions:
        - If the file already exists at the specified path.
        - If the file's name matches any pattern in the ignore list.
        - If the file's name does not match any pattern in the include list.

        If any of these conditions are met, the download is skipped, and appropriate
        logs are updated.
        """
        ignore_list = getattr(self.args, "ignore", [])
        include_list = getattr(self.args, "include", [])

        # Check if the file already exists
        if Path(final_path).exists():
            self.live_manager.update_log(
                "Skipped download",
                f"{self.file_name} has already been downloaded.",
            )
            self.live_manager.update_task(self.task, completed=100, visible=False)
            return True

        # Check if the file is in the ignore list (if specified)
        if ignore_list:
            is_in_ignore = any(word in self.file_name for word in ignore_list)
            if is_in_ignore:
                self.live_manager.update_log(
                    "Skipped download",
                    f"{self.file_name} was skipped because it contains "
                    "words in the ignore list.",
                )
                self.live_manager.update_task(self.task, completed=100, visible=False)
                return True

        # Check if the file is not in the include list (if specified)
        if include_list:
            not_in_include = all(word not in self.file_name for word in include_list)
            if not_in_include:
                self.live_manager.update_log(
                    "Skipped download",
                    f"{self.file_name} was skipped because it does not contain "
                    "words in the include list.",
                )
                self.live_manager.update_task(self.task, completed=100, visible=False)
                return True

        # If none of the skip conditions are met, return False (do not skip)
        return False

    def attempt_download(self, final_path: str) -> bool:
        """Attempt to download the file with retries."""
        for attempt in range(self.retries):
            try:
                response = requests.get(
                    self.download_link,
                    stream=True,
                    headers=HEADERS,
                    timeout=30,
                )
                response.raise_for_status()

                partial_download = save_file_with_progress(
                    response,
                    final_path,
                    self.task,
                    self.live_manager,
                )
                if partial_download:
                    self.handle_partial_download()

                # Exit the loop if the download is successful
                return False

            except RequestException as req_err:
                # Exit the loop if not retrying
                if not self.handle_request_exception(req_err, attempt):
                    break

        # Download failed
        return True

    def handle_partial_download(self) -> None:
        """Handle cases where a file is only partially downloaded."""
        self.live_manager.update_log(
            "Partial download",
            f"The extension of {self.file_name} has been modified to '.temp' "
            "because of empty data blocks. Check the log file.",
        )
        write_on_session_log(self.download_link)
        self.live_manager.update_task(
            self.task,
            completed=100,
            visible=False,
        )

    def handle_request_exception(self, req_err: RequestException, attempt: int) -> bool:
        """Handle exceptions during the request and manages retries."""
        is_server_down = (
            req_err.response is None
            or req_err.response.status_code == HTTP_STATUS_SERVER_DOWN
        )
        if is_server_down:
            # Mark the subdomain as offline and exit the loop
            marked_subdomain = mark_subdomain_as_offline(
                self.bunkr_status,
                self.download_link,
            )
            self.live_manager.update_log(
                "No response",
                f"Subdomain {marked_subdomain} has been marked as offline.",
            )
            return False

        if req_err.response.status_code in (429, 503):
            self.live_manager.update_log(
                "Too many requests",
                f"Retrying to download {self.file_name}... "
                f"({attempt + 1}/{self.retries})",
            )
            if attempt < self.retries - 1:
                # Retry the request
                delay = 4 ** (attempt + 1) + random.uniform(2, 4)
                time.sleep(delay)
                return True

        if req_err.response.status_code == HTTP_STATUS_BAD_GATEWAY:
            self.live_manager.update_log(
                "Server error",
                f"Bad gateway for {self.file_name}.",
            )
            # Setting retries to 1 forces an immediate failure on the next check.
            self.retries = 1
            return False

        # Do not retry, exit the loop
        self.live_manager.update_log("Request error", str(req_err))
        return False

    def handle_failed_download(self, is_final_attempt: bool) -> dict | None:
        """Handle a failed download after all retry attempts."""
        if not is_final_attempt:
            self.live_manager.update_log(
                "Exceeded retry attempts",
                f"Exceeded retry attempts for {self.file_name}. "
                "It will be retried one more time after all other tasks.",
            )
            return {
                "id": self.task,
                "file_name": self.file_name,
                "download_link": self.download_link,
            }

        self.live_manager.update_log(
            "Download failed",
            f"Failed to download {self.file_name}. The failure has been logged.",
        )
        self.live_manager.update_task(self.task, visible=False)
        return None

    def download(self) -> None:
        """Handle the download process."""
        is_final_attempt = self.retries == 1
        is_offline = subdomain_is_offline(
            self.download_link,
            self.bunkr_status,
        )

        if is_offline and is_final_attempt:
            self.live_manager.update_log(
                "Non-operational subdomain",
                f"The subdomain for {self.file_name} appears to be offline. "
                "Check the log file.",
            )
            write_on_session_log(self.download_link)
            self.live_manager.update_task(self.task, visible=False)
            return None

        final_path = str(Path(self.download_path) / self.file_name)

        # Skip download if the file exists or is blacklisted
        if self.skip_file_download(final_path):
            return None

        # Attempt to download the file with retries
        failed_download = self.attempt_download(final_path)

        # Handle failed download after retries
        if failed_download:
            return self.handle_failed_download(is_final_attempt)

        return None
