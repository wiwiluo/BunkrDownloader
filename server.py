"""Web server for Bunkr URL resolver.

Provides a simple web interface where users can paste Bunkr URLs
(album or single-file) and get back the real download links with filenames.

Usage:
    python server.py
    → Open http://127.0.0.1:5000 in your browser.
"""

from __future__ import annotations

import asyncio
import json
import logging
import queue
import sys
import threading

from flask import Flask, Response, jsonify, render_template, request, send_from_directory, stream_with_context

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

async def _resolve_single_url(
    url: str,
    progress_queue: queue.Queue | None = None,
) -> dict:
    """解析单个 Bunkr URL（专辑或单文件）。

    若提供 progress_queue，则解析专辑时会逐文件推送进度事件。

    返回 ``{"results": list[dict], "errors": list[dict]}``。
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

        total_items = len(item_pages)
        if progress_queue is not None:
            progress_queue.put({
                "type": "sub_start",
                "url": url,
                "total": total_items,
            })

        for idx, item_page in enumerate(item_pages):
            try:
                item_soup = await fetch_page(item_page)
                if item_soup is None:
                    errors.append(
                        {"url": item_page, "error": "无法访问子页面"},
                    )
                    if progress_queue is not None:
                        progress_queue.put({
                            "type": "sub_progress",
                            "url": url,
                            "current": idx + 1,
                            "total": total_items,
                        })
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

            if progress_queue is not None:
                progress_queue.put({
                    "type": "sub_progress",
                    "url": url,
                    "current": idx + 1,
                    "total": total_items,
                })

    # ---- Single file ----
    else:
        if progress_queue is not None:
            progress_queue.put({
                "type": "sub_start",
                "url": url,
                "total": 1,
            })

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

        if progress_queue is not None:
            progress_queue.put({
                "type": "sub_progress",
                "url": url,
                "current": 1,
                "total": 1,
            })

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
    """Accept a JSON body ``{"urls": ["...", "..."]}`` and stream progress via SSE."""
    data = request.get_json(silent=True)
    if not data or "urls" not in data:
        return jsonify({"error": '缺少 "urls" 参数'}), 400

    raw_urls: list[str] = data["urls"]
    urls = [u.strip() for u in raw_urls if u.strip()]
    if not urls:
        return jsonify({"results": [], "errors": []})

    def _sse(data: dict) -> str:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    def generate():
        total = len(urls)
        all_results: list[dict] = []
        all_errors: list[dict] = []

        yield _sse({"type": "start", "total": total})

        for i, url in enumerate(urls):
            yield _sse({
                "type": "progress",
                "current": i + 1,
                "total": total,
                "url": url,
            })

            # 使用线程 + 队列获取专辑内逐文件解析进度
            q: queue.Queue = queue.Queue()
            outcome_container: dict = {}

            def _run() -> None:
                try:
                    outcome_container["data"] = asyncio.run(
                        _resolve_single_url(url, progress_queue=q),
                    )
                except Exception as exc:  # noqa: BLE001
                    outcome_container["error"] = exc
                finally:
                    q.put(None)  # 哨兵，表示解析完成

            t = threading.Thread(target=_run)
            t.start()

            # 逐条读取进度事件并推送到前端
            while True:
                msg = q.get()
                if msg is None:
                    break
                yield _sse(msg)

            t.join()

            if "error" in outcome_container:
                logging.exception(
                    "Unexpected error resolving %s", url,
                )
                err_item = {"url": url, "error": str(outcome_container["error"])}
                all_errors.append(err_item)
                yield _sse({
                    "type": "url_done",
                    "url": url,
                    "files_found": 0,
                    "error_count": 1,
                    "error_items": [err_item],
                })
                continue

            outcome = outcome_container["data"]
            all_results.extend(outcome["results"])
            all_errors.extend(outcome["errors"])
            yield _sse({
                "type": "url_done",
                "url": url,
                "files_found": len(outcome["results"]),
                "error_count": len(outcome["errors"]),
                "error_items": outcome["errors"],
            })

        yield _sse({
            "type": "complete",
            "results": all_results,
            "errors": all_errors,
        })

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"X-Accel-Buffering": "no"},
    )


@app.route("/favicon.ico")
def favicon():
    """Serve the favicon."""
    return send_from_directory("assets", "favicon.ico", mimetype="image/vnd.microsoft.icon")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("🌐 Bunkr URL 解析器已启动 → http://127.0.0.1:5000", file=sys.stderr)
    app.run(host="0.0.0.0", port=5000, debug=False)
