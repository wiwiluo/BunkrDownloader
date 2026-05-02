DROP DATABASE IF EXISTS bunkr_downloader;

CREATE DATABASE bunkr_downloader
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE bunkr_downloader;

DROP DATABASE IF EXISTS bunkr_downloader;

CREATE DATABASE bunkr_downloader
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE bunkr_downloader;

-- 查询会话表：记录每次用户的批量查询请求
drop table if exists query_sessions;
CREATE TABLE query_sessions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    session_id VARCHAR(64) NOT NULL UNIQUE COMMENT '会话唯一标识（UUID）',
    client_ip VARCHAR(45) DEFAULT NULL COMMENT '客户端IP地址',
    user_agent VARCHAR(500) DEFAULT NULL COMMENT '用户代理字符串',
    total_urls INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '提交的URL总数',
    status ENUM('processing', 'completed', 'failed', 'cancelled') NOT NULL DEFAULT 'processing' COMMENT '会话状态',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    completed_at TIMESTAMP NULL DEFAULT NULL COMMENT '完成时间',
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='查询会话表';

-- URL查询记录表：记录每个被查询的原始URL
drop table if exists url_queries;
CREATE TABLE url_queries (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    session_id VARCHAR(64) NOT NULL COMMENT '关联的会话ID',
    original_url VARCHAR(2048) NOT NULL COMMENT '原始查询URL',
    url_type ENUM('album', 'single', 'unknown') NOT NULL DEFAULT 'unknown' COMMENT 'URL类型：专辑/单文件/未知',
    status ENUM('pending', 'success', 'failed', 'cancelled') NOT NULL DEFAULT 'pending' COMMENT '解析状态',
    error_message TEXT DEFAULT NULL COMMENT '错误信息（如果失败）',
    sort_order INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '在会话中的排序顺序',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (session_id) REFERENCES query_sessions(session_id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='URL查询记录表';

-- 解析结果表：记录解析成功的文件信息
drop table if exists parse_results;
CREATE TABLE parse_results (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    query_id BIGINT UNSIGNED NOT NULL COMMENT '关联的查询记录ID',
    session_id VARCHAR(64) NOT NULL COMMENT '关联的会话ID（冗余，便于查询）',
    filename VARCHAR(1024) NOT NULL COMMENT '文件名',
    download_url VARCHAR(2048) NOT NULL COMMENT '真实下载地址',
    source_url VARCHAR(2048) NOT NULL COMMENT '来源页面URL',
    file_size BIGINT UNSIGNED DEFAULT NULL COMMENT '文件大小（字节）',
    file_type VARCHAR(50) DEFAULT NULL COMMENT '文件类型（扩展名）',
    is_downloaded TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已下载：0-未下载，1-已下载',
    downloaded_at TIMESTAMP NULL DEFAULT NULL COMMENT '下载完成时间',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (query_id) REFERENCES url_queries(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES query_sessions(session_id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_query_id (query_id),
    INDEX idx_created_at (created_at),
    INDEX idx_is_downloaded (is_downloaded)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='解析结果表';

-- 下载操作记录表：记录用户的下载操作（Motrix发送、复制链接等）
drop table if exists download_actions;
CREATE TABLE download_actions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    result_id BIGINT UNSIGNED NOT NULL COMMENT '关联的解析结果ID',
    session_id VARCHAR(64) NOT NULL COMMENT '关联的会话ID',
    action_type ENUM('motrix', 'copy_url', 'manual') NOT NULL COMMENT '操作类型：Motrix下载/复制链接/手动下载',
    action_status ENUM('success', 'failed', 'pending') NOT NULL DEFAULT 'success' COMMENT '操作状态',
    client_ip VARCHAR(45) DEFAULT NULL COMMENT '客户端IP地址',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    FOREIGN KEY (result_id) REFERENCES parse_results(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES query_sessions(session_id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_result_id (result_id),
    INDEX idx_action_type (action_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='下载操作记录表';

-- 统计视图：会话级别的统计信息
DROP VIEW IF EXISTS session_statistics;
CREATE VIEW session_statistics AS
SELECT
    qs.session_id,
    qs.client_ip,
    qs.total_urls,
    qs.status AS session_status,
    qs.created_at,
    qs.completed_at,
    COUNT(DISTINCT uq.id) AS queried_url_count,
    SUM(CASE WHEN uq.status = 'success' THEN 1 ELSE 0 END) AS success_url_count,
    SUM(CASE WHEN uq.status = 'failed' THEN 1 ELSE 0 END) AS failed_url_count,
    COUNT(pr.id) AS total_files_found,
    SUM(CASE WHEN pr.is_downloaded = 1 THEN 1 ELSE 0 END) AS downloaded_file_count,
    TIMESTAMPDIFF(SECOND, qs.created_at, qs.completed_at) AS duration_seconds
FROM query_sessions qs
LEFT JOIN url_queries uq ON qs.session_id = uq.session_id
LEFT JOIN parse_results pr ON uq.id = pr.query_id
GROUP BY qs.session_id;

-- 常用查询示例索引优化
-- 1. 按时间范围查询会话
CREATE INDEX idx_session_time_range ON query_sessions(created_at, status);

-- 2. 按URL模糊搜索
CREATE INDEX idx_original_url_search ON url_queries(original_url(255));

-- 3. 热门文件统计
CREATE INDEX idx_filename_stats ON parse_results(filename(255), created_at);
