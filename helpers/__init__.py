"""
The `helpers` package provides utility modules and functions to support 
the main application. These utilities include functions for downloading, 
file management, URL handling, progress tracking, and more.

Modules:
    - bunkr_utils: Functions for checking Bunkr status and URL validation.
    - download_utils: Functions for handling downloads.
    - file_utils: Utilities for managing file operations.
    - general_utils: Miscellaneous utility functions.
    - playwright_crawler: Module that utilizes Playwright to automate media
                          crawling from Bunkr.
    - url_utils: Utilities to analyze and extract details from URLs.

This package is designed to be reusable and modular, allowing its components 
to be easily imported and used across different parts of the application.
"""

# helpers/__init__.py

__all__ = [
    "bunkr_utils",
    "download_utils",
    "file_utils",
    "general_utils",
    "playwright_crawler",
    "url_utils"
]
