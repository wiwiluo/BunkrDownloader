"""Module that provides utilities for interacting with the Bunkr API."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from src.config import BUNKR_API, JS_VARS_REGEX

if TYPE_CHECKING:
    import aiohttp
    from bs4 import BeautifulSoup


def unescape_js_path(value: str) -> str:
    """Unescape common JavaScript-escaped URL fragments."""
    return value.replace(r"\/", "/")


def extract_js_vars(soup: BeautifulSoup) -> dict[str, str]:
    """Extract runtime variables embedded in Bunkr inline JavaScript."""
    for script in soup.find_all("script"):
        if script.string and "var jsCDN" in script.string:
            matches = re.compile(JS_VARS_REGEX, re.DOTALL).findall(script.string)
            return {key: unescape_js_path(value).strip("\"'") for key, value in matches}
    return {}


async def get_api_response(
    session: aiohttp.ClientSession, item_url: str, soup: BeautifulSoup | None = None,
) -> str | None:
    """Fetch encryption data from the Bunkr API."""
    js_vars = extract_js_vars(soup)
    js_cdn = js_vars.get("jsCDN") if js_vars else None
    js_slug = PurePosixPath(urlparse(item_url).path).name
    js_cdn_path = urlparse(js_cdn).path if js_cdn else f"/storage/media/{js_slug}"

    async with session.get(BUNKR_API, params={"path": js_cdn_path}) as response:
        sign_data = await response.json()

    token = sign_data.get("token")
    ex = sign_data.get("ex")
    if token and ex:
        return f"{js_cdn}?token={token}&ex={ex}"

    return js_cdn
