"""
Centralized configuration module for managing constants and settings used
across the project. These configurations aim to improve modularity and
readability by consolidating settings into a single location.
"""

STATUS_PAGE = "https://status.bunkr.ru/"  # The URL of the status page for
                                          # checking service availability.
DOWNLOAD_FOLDER = "Downloads"             # The folder where downloaded files
                                          # will be stored.
FILE = "URLs.txt"                         # The name of the file containing the
                                          # list of URLs to process.
SESSION_LOG = "session_log.txt"           # The file used to log session errors.

# Headers used for general HTTP requests, mimicking a browser user agent.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) "
        "Gecko/20100101 Firefox/117.0"
    )
}

# Headers specifically tailored for download requests.
DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) "
        "Gecko/20100101 Firefox/117.0"
    ),
    "Connection": "keep-alive",
    "Referer": "https://get.bunkrr.su/"
}

# Configuration for the browser automation module.
BROWSER_CONFIG = {
    "url": "https://9xbuddy.in/en",
    "input_selector": "input.w-full",
    "button_selector": r".w-8\/12",
    "download_button": (
        r"div.lg\:flex:nth-child(6) > div:nth-child(2) > a:nth-child(1)"
    ),
    "attribute": "href",
    "button_timeout": 5000
}
