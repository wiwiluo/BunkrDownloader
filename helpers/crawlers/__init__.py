"""
The `crawlers` package provides utility modules and functions to support
the main application. These utilities include functions for media crawling,
URL handling, and more.

Modules:
    - crawler_utils: Module with utility functions for crawling and handling
                     URLs.
    - playwright_crawler: Module that utilizes Playwright to automate media
                          crawling from Bunkr.

This package is designed to be reusable and modular, allowing its components 
to be easily imported and used across different parts of the application.
"""

# crawlers/__init__.py

__all__ = [
    "crawler_utils",
    "playwright_crawler"
]
