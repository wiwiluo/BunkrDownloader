"""PostgreSQL 数据库连接与操作模块。

提供连接池初始化、建表、保存解析记录、更新完成状态、历史查询等功能。
数据库不可用时，所有操作静默返回 None/空，保证解析功能不受影响。
"""

from __future__ import annotations

import logging
from configparser import ConfigParser
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

from src.crypto_utils import get_db_password

# 配置文件路径（项目根目录）
_CONFIG_PATH = Path(__file__).parent.parent / "db_config.ini"


def _load_db_config() -> dict[str, str | int]:
    """从 INI 配置文件读取数据库连接参数。"""
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(f"数据库配置文件不存在：{_CONFIG_PATH}")
    parser = ConfigParser()
    parser.read(_CONFIG_PATH, encoding="utf-8")
    section = parser["postgresql"]
    return {
        "host": section["host"],
        "port": section.getint("port"),
        "user": section["user"],
        "database": section["database"],
    }


DB_CONFIG = _load_db_config()

# 连接池（全局单例）
_pool: SimpleConnectionPool | None = None


def init_db() -> str | None:
    """初始化数据库连接池并创建表结构。

    数据库连接失败时仅记录警告，允许应用以降级模式运行。

    Returns:
        成功返回 None，失败返回错误信息字符串。
    """
    global _pool  # noqa: PLW0603

    try:
        password = get_db_password()
        _pool = SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            **DB_CONFIG,
            password=password,
        )
        _init_tables()
        logging.info("数据库连接池初始化成功")
        return None
    except Exception as exc:
        error_msg = (
            f"数据库初始化失败（{DB_CONFIG['host']}:{DB_CONFIG['port']}"
            f"/{DB_CONFIG['database']}）：{exc}"
        )
        logging.warning("%s，将以无数据库模式运行", error_msg)
        _pool = None
        return error_msg


def _init_tables() -> None:
    """创建表结构（如果不存在）。"""
    ddl = """
    CREATE TABLE IF NOT EXISTS parse_records (
        id           BIGSERIAL       PRIMARY KEY,
        original_url TEXT            NOT NULL,
        status       VARCHAR(20)     NOT NULL DEFAULT 'pending',
        file_count   INTEGER         NOT NULL DEFAULT 0,
        created_at   TIMESTAMP       NOT NULL DEFAULT NOW(),
        updated_at   TIMESTAMP       NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS parse_results (
        id             BIGSERIAL       PRIMARY KEY,
        record_id      BIGINT          NOT NULL REFERENCES parse_records(id) ON DELETE CASCADE,
        thumbnail_url  TEXT            DEFAULT '',
        filename       VARCHAR(1024)   NOT NULL,
        source_url     TEXT            NOT NULL,
        download_url   TEXT            NOT NULL,
        is_completed   BOOLEAN         NOT NULL DEFAULT FALSE,
        created_at     TIMESTAMP       NOT NULL DEFAULT NOW()
    );
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()


@contextmanager
def _get_conn():
    """从连接池获取连接的上下文管理器。"""
    global _pool  # noqa: PLW0603
    if _pool is None:
        raise RuntimeError("数据库连接池未初始化")
    conn = _pool.getconn()
    try:
        yield conn
    finally:
        _pool.putconn(conn)


def save_parse_record(
    url: str,
    results: list[dict],
) -> tuple[int, list[int]] | None:
    """保存一条解析记录及其所有结果。

    若该 URL 已解析成功，跳过保存并返回 None（避免重复记录）。

    Args:
        url: 用户输入的原始 URL。
        results: 解析结果列表，每项含 filename、download_url、source_url、thumbnail_url。

    Returns:
        (record_id, [result_id, ...]) 元组；若数据库不可用或 URL 已存在则返回 None。
    """
    if _pool is None:
        return None

    # 检查是否已存在成功记录，避免重复保存
    if check_url_already_parsed(url):
        logging.info("URL 已存在解析记录，跳过保存：%s", url)
        return None

    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                status = "completed" if results else "failed"
                cur.execute(
                    "INSERT INTO parse_records (original_url, status, file_count) "
                    "VALUES (%s, %s, %s) RETURNING id",
                    (url, status, len(results)),
                )
                record_id = cur.fetchone()[0]

                result_ids: list[int] = []
                for r in results:
                    cur.execute(
                        "INSERT INTO parse_results "
                        "(record_id, thumbnail_url, filename, source_url, download_url) "
                        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                        (
                            record_id,
                            r.get("thumbnail_url", ""),
                            r["filename"],
                            r["source_url"],
                            r["download_url"],
                        ),
                    )
                    result_ids.append(cur.fetchone()[0])

                conn.commit()
                return record_id, result_ids
    except Exception as exc:
        logging.exception("保存解析记录失败：%s", exc)
        return None


def mark_result_completed(result_id: int) -> bool:
    """将指定解析结果标记为已完成。

    Args:
        result_id: 解析结果 ID。

    Returns:
        是否更新成功。
    """
    if _pool is None:
        return False

    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE parse_results SET is_completed = TRUE WHERE id = %s",
                    (result_id,),
                )
                conn.commit()
                return cur.rowcount > 0
    except Exception as exc:
        logging.exception("更新完成状态失败：%s", exc)
        return False


def delete_result(result_id: int) -> bool:
    """删除单条解析结果。

    Args:
        result_id: 解析结果 ID。

    Returns:
        是否删除成功。
    """
    if _pool is None:
        return False

    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM parse_results WHERE id = %s",
                    (result_id,),
                )
                conn.commit()
                return cur.rowcount > 0
    except Exception as exc:
        logging.exception("删除解析结果失败：%s", exc)
        return False


def delete_results_batch(ids: list[int]) -> int:
    """批量删除解析结果。

    Args:
        ids: 要删除的解析结果 ID 列表。

    Returns:
        实际删除的条数，数据库不可用时返回 0。
    """
    if _pool is None or not ids:
        return 0

    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM parse_results WHERE id = ANY(%s)",
                    (ids,),
                )
                conn.commit()
                return cur.rowcount
    except Exception as exc:
        logging.exception("批量删除失败：%s", exc)
        return 0


def delete_all_records() -> int:
    """清空所有解析记录和结果。

    Returns:
        删除的记录总数。
    """
    if _pool is None:
        return 0

    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS cnt FROM parse_results")
                count = cur.fetchone()[0]
                # 利用 ON DELETE CASCADE，删除 parse_records 会自动删除 parse_results
                cur.execute("DELETE FROM parse_records")
                conn.commit()
                return count
    except Exception as exc:
        logging.exception("清空记录失败：%s", exc)
        return 0


def check_url_already_parsed(url: str) -> bool:
    """检查 URL 是否已经解析过（已有成功记录）。

    Args:
        url: 原始 URL。

    Returns:
        是否已存在该 URL 的成功解析记录。
    """
    if _pool is None:
        return False

    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM parse_records "
                    "WHERE original_url = %s AND status = 'completed'",
                    (url,),
                )
                return cur.fetchone()[0] > 0
    except Exception as exc:
        logging.exception("检查 URL 是否存在失败：%s", exc)
        return False


def query_history(
    page: int = 1,
    per_page: int = 20,
    search: str = "",
) -> dict[str, Any]:
    """分页查询历史解析结果，按时间降序排列。

    Args:
        page: 页码，从 1 开始。
        per_page: 每页条数。
        search: 文件名模糊搜索关键词（可选）。

    Returns:
        包含 results、total、page、total_pages 的字典。
    """
    if _pool is None:
        return {"results": [], "total": 0, "page": page, "total_pages": 0}

    offset = (page - 1) * per_page

    try:
        with _get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if search:
                    like_pattern = f"%{search}%"
                    cur.execute(
                        "SELECT pr.id, pr.thumbnail_url, pr.filename, "
                        "pr.source_url, pr.download_url, pr.is_completed, "
                        "pr.created_at, po.original_url "
                        "FROM parse_results pr "
                        "JOIN parse_records po ON pr.record_id = po.id "
                        "WHERE pr.filename ILIKE %s "
                        "ORDER BY pr.created_at DESC "
                        "LIMIT %s OFFSET %s",
                        (like_pattern, per_page, offset),
                    )
                    results = cur.fetchall()
                    cur.execute(
                        "SELECT COUNT(*) AS cnt FROM parse_results "
                        "WHERE filename ILIKE %s",
                        (like_pattern,),
                    )
                else:
                    cur.execute(
                        "SELECT pr.id, pr.thumbnail_url, pr.filename, "
                        "pr.source_url, pr.download_url, pr.is_completed, "
                        "pr.created_at, po.original_url "
                        "FROM parse_results pr "
                        "JOIN parse_records po ON pr.record_id = po.id "
                        "ORDER BY pr.created_at DESC "
                        "LIMIT %s OFFSET %s",
                        (per_page, offset),
                    )
                    results = cur.fetchall()
                    cur.execute("SELECT COUNT(*) AS cnt FROM parse_results")

                total = cur.fetchone()["cnt"]

        return {
            "results": results,
            "total": total,
            "page": page,
            "total_pages": max(1, (total + per_page - 1) // per_page),
        }
    except Exception as exc:
        logging.exception("查询历史记录失败：%s", exc)
        return {"results": [], "total": 0, "page": page, "total_pages": 0}
