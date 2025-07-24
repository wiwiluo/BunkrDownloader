"""Configuration module for managing constants and settings used across the project.

These configurations aim to improve modularity and readability by consolidating settings
into a single location.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Namespace

STATUS_PAGE = "https://status.bunkr.ru/"    # The URL of the status page for checking
                                            # service availability.
BUNKR_API = "https://bunkr.cr/api/vs"       # The API for retrieving encryption data.

DOWNLOAD_FOLDER = "Downloads"               # The folder where downloaded files
                                            # will be stored.
FILE = "URLs.txt"                           # The name of the file containing the
                                            # list of URLs to process.
SESSION_LOG = "session_log.txt"             # The file used to log errors.

MAX_FILENAME_LEN = 120                      # The maximum length for a file name.
MAX_WORKERS = 3                             # The maximum number of threads for
                                            # concurrent downloads.

# Regex used to extract and validate the media slug
VALID_SLUG_REGEX = r"^[a-zA-Z0-9_-]+$"
MEDIA_SLUG_REGEX = r'const\s+slug\s*=\s*"([a-zA-Z0-9_-]+)"'

# Constants for file sizes, expressed in bytes.
KB = 1024
MB = 1024 * KB
GB = 1024 * MB

# Thresholds for file sizes and corresponding chunk sizes used during download.
# Each tuple represents: (file size threshold, chunk size to download in that range).
THRESHOLDS = [
    (1 * MB, 32 * KB),    # Less than 1 MB
    (10 * MB, 128 * KB),  # 1 MB to 10 MB
    (50 * MB, 512 * KB),  # 10 MB to 50 MB
    (100 * MB, 1 * MB),   # 50 MB to 100 MB
    (250 * MB, 2 * MB),   # 100 MB to 250 MB
    (500 * MB, 4 * MB),   # 250 MB to 500 MB
    (1 * GB, 8 * MB),     # 500 MB to 1 GB
]

# Default chunk size for files larger than the largest threshold.
LARGE_FILE_CHUNK_SIZE = 16 * MB

# HTTP status codes.
HTTP_STATUS_OK = 200
HTTP_STATUS_FORBIDDEN = 403
HTTP_STATUS_BAD_GATEWAY = 502
HTTP_STATUS_SERVER_DOWN = 521

# Headers used for general HTTP requests.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) "
        "Gecko/20100101 Firefox/136.0"
    ),
}

# Headers specifically tailored for download requests.
DOWNLOAD_HEADERS = {
    **HEADERS,
    "Connection": "keep-alive",
    "Referer": "https://get.bunkrr.su/",
}

@dataclass
class DownloadInfo:
    """Represent the information related to a download task."""

    download_link: str
    filename: str
    task: int

@dataclass
class SessionInfo:
    """Hold the session-related information."""

    args: Namespace | None
    bunkr_status: dict[str, str]
    download_path: str

@dataclass
class AlbumInfo:
    """Store the informations about an album and its associated item pages."""

    album_id: str
    item_pages: list[str]
