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
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, send_from_directory, stream_with_context

from src.config import VIDEO_EXTENSIONS
from src.crawlers.crawler_utils import (
    extract_all_album_item_pages,
    get_download_info,
    get_item_thumbnail,
)
from src.database import (
    delete_all_records,
    delete_result,
    delete_results_batch,
    init_db,
    mark_result_completed,
    query_history,
    save_parse_record,
)
from src.general_utils import fetch_page
from src.url_utils import add_https_prefix, check_url_type, get_host_page

logging.basicConfig(level=logging.WARNING)

app = Flask(__name__)

# 初始化数据库连接池（失败时降级运行）
_db_error = init_db()
if _db_error is not None:
    print(f"⚠️  {_db_error}", file=sys.stderr)
    print("⚠️  将以无数据库模式运行，解析功能不受影响", file=sys.stderr)


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
                    ext = Path(filename).suffix.lower()
                    if ext in VIDEO_EXTENSIONS:
                        thumbnail_url = get_item_thumbnail(item_soup)
                        results.append(
                            {
                                "filename": filename,
                                "download_url": dl_link,
                                "source_url": item_page,
                                "thumbnail_url": thumbnail_url,
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
                thumbnail_url = get_item_thumbnail(soup)
                results.append(
                    {
                        "filename": filename,
                        "download_url": dl_link,
                        "source_url": validated_url,
                        "thumbnail_url": thumbnail_url,
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

            # 将解析结果保存到数据库，并将 result_id 附加到结果中供前端使用
            db_result = save_parse_record(url, outcome["results"])
            if db_result is not None:
                _record_id, result_ids = db_result
                for j, r in enumerate(outcome["results"]):
                    if j < len(result_ids):
                        r["result_id"] = result_ids[j]

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


@app.route("/api/complete", methods=["POST"])
def api_complete():
    """将指定解析结果标记为已完成。"""
    data = request.get_json(silent=True)
    if not data or "result_id" not in data:
        return jsonify({"success": False, "error": "缺少 result_id 参数"}), 400

    result_id = data["result_id"]
    success = mark_result_completed(result_id)
    if success:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "更新失败，数据库可能不可用"}), 500


@app.route("/history")
def history():
    """历史记录查询页面。"""
    return render_template("history.html")


@app.route("/api/history")
def api_history():
    """分页查询历史解析结果，支持文件名模糊搜索。

    Query params:
        page: 页码，默认 1。
        per_page: 每页条数，默认 20，最大 100。
        search: 文件名模糊搜索关键词。
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "", type=str).strip()

    page = max(1, page)
    per_page = max(1, min(100, per_page))

    data = query_history(page=page, per_page=per_page, search=search)

    # 将 RealDictRow 转换为可 JSON 序列化的普通字典
    results = []
    for row in data["results"]:
        results.append({
            "id": row["id"],
            "thumbnail_url": row["thumbnail_url"],
            "filename": row["filename"],
            "source_url": row["source_url"],
            "download_url": row["download_url"],
            "is_completed": row["is_completed"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "original_url": row["original_url"],
        })

    return jsonify({
        "results": results,
        "total": data["total"],
        "page": data["page"],
        "total_pages": data["total_pages"],
    })


@app.route("/api/history/<int:result_id>", methods=["DELETE"])
def api_delete_result(result_id: int):
    """删除单条解析结果。"""
    success = delete_result(result_id)
    if success:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "删除失败"}), 500


@app.route("/api/history/batch-delete", methods=["POST"])
def api_batch_delete():
    """批量删除解析结果。

    Body: {"ids": [1, 2, 3]} → {"success": true, "deleted_count": N}
    """
    data = request.get_json(silent=True)
    if not data or "ids" not in data:
        return jsonify({"success": False, "error": "缺少 ids 参数"}), 400

    ids = data["ids"]
    if not isinstance(ids, list) or not ids:
        return jsonify({"success": False, "error": "ids 必须是非空数组"}), 400

    count = delete_results_batch(ids)
    return jsonify({"success": True, "deleted_count": count})


@app.route("/api/history/clear", methods=["DELETE"])
def api_clear_history():
    """清空所有解析记录。"""
    count = delete_all_records()
    return jsonify({"success": True, "deleted_count": count})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("🌐 Bunkr URL 解析器已启动 → http://127.0.0.1:5000", file=sys.stderr)
    app.run(host="0.0.0.0", port=5000, debug=False)
