"""Utilities for handling file downloads with progress tracking."""

import logging
import shutil
from pathlib import Path

from requests import Response

from helpers.config import LARGE_FILE_CHUNK_SIZE, THRESHOLDS
from helpers.managers.progress_manager import ProgressManager


def get_chunk_size(file_size: int) -> int:
    """Determine the optimal chunk size based on the file size."""
    for threshold, chunk_size in THRESHOLDS:
        if file_size < threshold:
            return chunk_size

    # Return a default chunk size for files larger than the largest threshold
    return LARGE_FILE_CHUNK_SIZE

def save_file_with_progress(
        response: Response,
        download_path: str,
        task: int,
        progress_manager: ProgressManager,
    ) -> bool:
    """Save the file from the response to the specified path.

    Adds a `.temp` extension if the download is partial.
    """
    file_size = int(response.headers.get("content-length", -1))
    if file_size == -1:
        logging.exception("Content length not provided in response headers.")

    # Create a temporary download path with the .temp extension
    temp_download_path = Path(download_path).with_suffix(".temp")

    chunk_size = get_chunk_size(file_size)
    total_downloaded = 0

    with temp_download_path.open("wb") as file:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk is not None:
                file.write(chunk)
                total_downloaded += len(chunk)
                completed = (total_downloaded / file_size) * 100
                progress_manager.update_task(task, completed=completed)

    # After download is complete, rename the temp file to the original filename
    if total_downloaded == file_size:
        shutil.move(temp_download_path, download_path)
        return False

    # Return True if the download is incomplete
    return True
