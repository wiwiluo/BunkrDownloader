"""Web server for Bunkr URL resolver.

Provides a simple web interface where users can paste Bunkr URLs
(album or single-file) and get back the real download links with filenames.

Usage:
    python server.py
    → Open http://127.0.0.1:5000 in your browser.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from flask import Flask, jsonify, render_template, request

from src.crawlers.crawler_utils import (
    extract_all_album_item_pages,
    get_download_info,
)
from src.general_utils import fetch_page
from src.url_utils import add_https_prefix, check_url_type, get_host_page

logging.basicConfig(level=logging.WARNING)

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _resolve_single_url(url: str) -> dict:
    """Resolve one Bunkr URL (album or single file).

    Returns ``{"results": list[dict], "errors": list[dict]}``.
    """
    validated_url = add_https_prefix(url.strip())
    soup = await fetch_page(validated_url)

    if soup is None:
        return {
            "results": [],
            "errors": [{"url": url, "error": "无法访问页面，请检查 URL 是否正确"}],
        }

    results: list[dict] = []
    errors: list[dict] = []

    # ---- Album ----
    if check_url_type(validated_url):
        host_page = get_host_page(validated_url)

        try:
            item_pages = await extract_all_album_item_pages(
                soup, host_page, validated_url,
            )
        except RuntimeError as exc:
            return {
                "results": [],
                "errors": [{"url": url, "error": str(exc)}],
            }

        for item_page in item_pages:
            try:
                item_soup = await fetch_page(item_page)
                if item_soup is None:
                    errors.append(
                        {"url": item_page, "error": "无法访问子页面"},
                    )
                    continue

                dl_link, filename = await get_download_info(item_page, item_soup)
                if dl_link:
                    results.append(
                        {
                            "filename": filename,
                            "download_url": dl_link,
                            "source_url": item_page,
                        },
                    )
                else:
                    errors.append(
                        {"url": item_page, "error": "无法解析下载链接"},
                    )
            except Exception as exc:  # noqa: BLE001
                errors.append({"url": item_page, "error": str(exc)})

    # ---- Single file ----
    else:
        try:
            dl_link, filename = await get_download_info(validated_url, soup)
            if dl_link:
                results.append(
                    {
                        "filename": filename,
                        "download_url": dl_link,
                        "source_url": validated_url,
                    },
                )
            else:
                errors.append(
                    {"url": url, "error": "无法解析下载链接"},
                )
        except Exception as exc:  # noqa: BLE001
            errors.append({"url": url, "error": str(exc)})

    return {"results": results, "errors": errors}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Serve the main page."""
    return render_template("index.html")


@app.route("/api/resolve", methods=["POST"])
def api_resolve():
    """Accept a JSON body ``{"urls": ["...", "..."]}`` and return resolved links."""
    data = request.get_json(silent=True)
    if not data or "urls" not in data:
        return jsonify({"error": '缺少 "urls" 参数'}), 400

    raw_urls: list[str] = data["urls"]
    if not raw_urls:
        return jsonify({"results": [], "errors": []})

    async def _process_all() -> dict:
        all_results: list[dict] = []
        all_errors: list[dict] = []
        for raw_url in raw_urls:
            url = raw_url.strip()
            if not url:
                continue
            result = await _resolve_single_url(url)
            all_results.extend(result["results"])
            all_errors.extend(result["errors"])
        return {"results": all_results, "errors": all_errors}

    try:
        outcome = asyncio.run(_process_all())
    except Exception as exc:  # noqa: BLE001
        logging.exception("Unexpected error during resolution")
        return jsonify({"error": f"服务器内部错误: {exc}"}), 500

    return jsonify(outcome)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("🌐 Bunkr URL 解析器已启动 → http://127.0.0.1:5000", file=sys.stderr)
    app.run(host="127.0.0.1", port=5000, debug=False)
