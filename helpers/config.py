"""Configuration module for managing constants and settings used across the project.

These configurations aim to improve modularity and readability by consolidating settings
into a single location.
"""

STATUS_PAGE = "https://status.bunkr.ru/"  # The URL of the status page for
                                          # checking service availability.
DOWNLOAD_FOLDER = "Downloads"             # The folder where downloaded files
                                          # will be stored.
FILE = "URLs.txt"                         # The name of the file containing the
                                          # list of URLs to process.
SESSION_LOG = "session_log.txt"           # The file used to log errors.
MAX_WORKERS = 4                           # The maximum number of threads for
                                          # concurrent downloads.

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
HTTP_STATUS_BAD_GATEWAY = 502
HTTP_STATUS_SERVER_DOWN = 521

# Headers used for general HTTP requests.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) "
        "Gecko/20100101 Firefox/117.0"
    ),
}

# Headers specifically tailored for download requests.
DOWNLOAD_HEADERS = {
    **HEADERS,
    "Connection": "keep-alive",
    "Referer": "https://get.bunkrr.su/",
}
