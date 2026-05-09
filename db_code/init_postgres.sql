-- ============================================================
-- BunkrDownloader PostgreSQL 数据库初始化脚本
-- 数据库名: bunkr_downloader
-- ============================================================

-- 创建数据库（需在 psql 中以 superuser 执行，或手动创建）
-- CREATE DATABASE bunkr_downloader;

-- 解析记录表（表1）：保存用户每次提交解析的 URL
CREATE TABLE IF NOT EXISTS parse_records (
    id           BIGSERIAL       PRIMARY KEY,
    original_url TEXT            NOT NULL,
    status       VARCHAR(20)     NOT NULL DEFAULT 'pending',
    file_count   INTEGER         NOT NULL DEFAULT 0,
    created_at   TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMP       NOT NULL DEFAULT NOW()
);

-- 解析结果表（表2）：保存每个文件的解析结果
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

-- 索引：按时间降序查询（历史记录页面）
CREATE INDEX IF NOT EXISTS idx_parse_records_created_at
    ON parse_records(created_at DESC);

-- 索引：按 record_id 关联查询
CREATE INDEX IF NOT EXISTS idx_parse_results_record_id
    ON parse_results(record_id);

-- 索引：按时间降序查询解析结果
CREATE INDEX IF NOT EXISTS idx_parse_results_created_at
    ON parse_results(created_at DESC);

-- 索引：文件名模糊搜索
CREATE INDEX IF NOT EXISTS idx_parse_results_filename
    ON parse_results(filename);
