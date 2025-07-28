"""Utilities functions for file input and output operations.

It includes methods to read the contents of a file and to write content to a file,
with optional support for clearing the file.
"""

import logging
import os
import platform
import shutil
import sys
from pathlib import Path

from .config import SESSION_LOG


def read_file(filename: str) -> list[str]:
    """Read the contents of a file and returns a list of its lines."""
    with Path(filename).open(encoding="utf-8") as file:
        return file.read().splitlines()


def write_file(filename: str, content: str = "") -> None:
    """Write content to a specified file.

    If content is not provided, the file is cleared.
    """
    with Path(filename).open("w", encoding="utf-8") as file:
        file.write(content)


def write_on_session_log(content: str) -> None:
    """Append content to the session log file."""
    with Path(SESSION_LOG).open("a", encoding="utf-8") as file:
        file.write(f"{content}\n")


def get_root_path() -> str:
    """Return the root path depending on the operating system."""
    if platform.system() == "Windows":
        # Use the system drive, e.g., "C:\\"
        return os.environ.get("SYSTEMDRIVE", "C:") + "\\"

    # For Linux and macOS
    return "/"


def check_python_version(min_version: tuple[int, int] = (3, 10)) -> None:
    """Check if the current Python version meets the minimum requirement."""
    current_version = sys.version_info
    if current_version < min_version:
        log_message = (
            f"Python {current_version.major}.{current_version.minor} is not supported. "
            f" Python {min_version[0]}.{min_version[1]} or higher is required.",
        )
        logging.warning(log_message)
        sys.exit(1)


def check_disk_space(min_space: int = 3) -> None:
    """Check if the available disk space is greater than or equal to `min_space` GB."""
    root_path = get_root_path()
    _, _, free_space = shutil.disk_usage(root_path)
    free_space_gb = free_space / (1024 ** 3)

    if free_space_gb < min_space:
        log_message = f"Insufficient disk space: only {free_space_gb:.2f} GB available."
        logging.warning(log_message)
        sys.exit(1)
