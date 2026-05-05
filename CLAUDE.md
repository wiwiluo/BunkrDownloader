# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 语言规范

1. 所有对话、解释、建议必须使用**简体中文**。
2. 代码注释必须使用中文。
3. 生成的 Commit Message 必须使用中文。
4. 严禁出现大段未翻译的英文技术名词（保留专业术语如 API、SDK 除外）。

## 技术栈

- Python ≥ 3.10
- `beautifulsoup4` — HTML 解析
- `requests` — HTTP 客户端
- `rich` — 终端 UI（进度条、实时表格）
- `Flask` — Web 解析器（仅 server.py）

## 常用命令

```bash
pip install -r requirements.txt

# 批量下载（读取 URLs.txt 中的 URL 列表）
python main.py

# 单 URL 下载（专辑或单个文件）
python downloader.py <url>

# 单 URL 下载 + 过滤器
python downloader.py <url> --ignore .zip --include photo

# 自定义下载路径
python downloader.py <url> --custom-path /path/to/drive

# 不创建 Downloads 子目录
python downloader.py <url> --no-download-folder

# 禁用 UI（Jupyter / CI 环境）
python downloader.py <url> --disable-ui

# 跳过磁盘空间检查
python downloader.py <url> --disable-disk-check

# 调整重试次数（默认 5）
python downloader.py <url> --max-retries 3

# 启动 Web 解析器（浏览器打开 http://127.0.0.1:5000）
python server.py

# 代码检查（ruff.toml: select = ["ALL"], line-length = 88）
ruff check .
```

## 架构概览

项目分为**三个入口**和**三个核心模块**：

### 入口文件

| 文件 | 用途 |
|---|---|
| `downloader.py` | CLI 单 URL 下载入口，解析参数后调用 `validate_and_download` |
| `main.py` | 批量下载入口，从 `URLs.txt` 逐行读取 URL，每次运行时备份 URL 文件到 `Backups/` |
| `server.py` | Flask Web 解析器，通过 SSE 流式返回解析到的下载链接和文件名；专辑解析时自动过滤非视频文件，并提取视频封面图 |

### src/ 核心模块

- **`src/crawlers/`** — 页面抓取与解密
  - `crawler_utils.py`：提取专辑分页、子页面链接、下载链接、文件名，以及视频封面图（og:image）
  - `api_utils.py`：调用 Bunkr API (`bunkr.cr/api/vs`) 获取加密数据，用 XOR + 时间密钥解密下载 URL

- **`src/downloaders/`** — 下载执行
  - `album_downloader.py`：`AlbumDownloader` 类，用 `asyncio.Semaphore` 控制并发（默认 3 线程），收集失败下载并统一重试
  - `media_downloader.py`：`MediaDownloader` 类，处理单文件下载、重试（指数退避）、跳过逻辑（已存在/忽略列表/包含列表/离线子域名）
  - `download_utils.py`：按文件大小选择分块大小，流式写入 `.temp` 临时文件，完成后重命名

- **`src/managers/`** — Rich 终端 UI
  - `live_manager.py`：`LiveManager` 统筹进度面板 + 日志面板 + 汇总统计
  - `progress_manager.py`：双列进度条（总进度 + 单任务进度），适应终端宽度
  - `log_manager.py`：`LoggerTable` 循环缓冲区日志表格，最多显示 4 行
  - `summary_manager.py`：`SummaryManager` 用 `Counter` 统计完成/失败/跳过的任务数及原因

### 数据类与配置

- `src/config.py`：所有常量、数据类（`AlbumInfo`、`DownloadInfo`、`SessionInfo`）、CLI 参数解析、HTTP 头、下载阈值、视频扩展名（`VIDEO_EXTENSIONS`）集中定义
- `src/url_utils.py`：URL 类型判断（`/a/` 专辑 vs `/f/` 文件）、专辑名提取、mojibake 修复（Latin-1 → UTF-8）
- `src/bunkr_utils.py`：从 Bunkr 状态页获取各子域名运行状态，离线子域名标记与检测
- `src/file_utils.py`：文件 I/O、目录创建、文件名截断/清理、session 日志写入
- `src/general_utils.py`：`fetch_page`（带重试和 fallback 域名切换）、磁盘空间检查、Python 版本检查
- `src/version.py`：语义化版本号 `1.1.9`

## 数据流

### 单 URL 下载流程

```
URL 输入 → add_https_prefix() → fetch_page()（403 时 fallback 到 bunkr.cr）
  → check_url_type() 判断 /a/（专辑）还是 /f/ 等（单文件）
  → 专辑路径：
     extract_all_album_item_pages() 收集子页面（含分页遍历）
     → AlbumDownloader.download_album() 并发下载
       每个子页面：fetch_page() → get_download_info()
         → get_api_response() 调 Bunkr API（POST /api/vs）获取加密数据
         → decrypt_url() XOR 解密得到真实下载链接
         → MediaDownloader.download() 执行下载
  → 单文件路径：直接 get_download_info() → MediaDownloader.download()
```

### 重试机制（两阶段）

1. **第一阶段**：`AlbumDownloader` 并发下载所有文件，单文件最多重试 `MAX_RETRIES`（默认 5）次，429 时指数退避（3^(attempt+1) + 随机抖动 1-3 秒）
2. **第二阶段**：`AlbumDownloader._process_failed_downloads()` 收集所有失败项，逐一重试 1 次

### Web 服务器 SSE 架构

`server.py` 使用 Flask 同步开发服务器。因 Flask 与 asyncio 不兼容，采用 `threading.Thread` + `asyncio.run()` 模式：

```
POST /api/resolve → generate() SSE 生成器
  → 每个输入 URL 启动独立 Thread，线程内 asyncio.run(_resolve_single_url())
  → 通过 queue.Queue 传递专辑内逐文件解析进度事件
  → SSE (text/event-stream) 推送到前端，事件类型：start / progress / sub_start /
    sub_progress / url_done / complete
```

前端 `templates/index.html` 是完整的单页应用（约 35KB），接收 SSE 事件逐文件渲染解析结果，表格含视频预览缩略图列。

专辑解析时，`_resolve_single_url` 会通过 `Path(filename).suffix` 检查文件扩展名是否在 `VIDEO_EXTENSIONS` 集合中，非视频文件不加入结果。封面图通过 `get_item_thumbnail()` 从 HTML `<meta property="og:image">` 标签提取，无需额外 API 调用。

### 启动时的状态检查

每次运行依次执行：
1. `check_python_version()` — 确保 Python ≥ 3.10
2. `get_bunkr_status()` — 从 `status.bunkr.ru` 抓取各 CDN 子域名运行状态
3. `check_disk_space()` — 确保可用空间 ≥ 3GB

下载过程中若子域名返回 521/503，`mark_subdomain_as_offline()` 将其标记为离线，后续文件自动跳过该子域名。

## 关键注意事项

- **无测试文件** — 项目未配置任何测试框架；CONTRIBUTING.md 中提及测试但实际未落地
- **URL 解密逻辑**（`api_utils.py`）：使用 `SECRET_KEY_{timestamp // 3600}` 做 XOR 解密，Bunkr 修改 API 格式会导致解密失效
- **`server.py` 中的 `asyncio.run()`**：在 Flask 开发服务器中能正常工作，但切换到 ASGI 服务器（gunicorn + uvicorn）会崩溃，因为每个请求新建事件循环
- **Rich Live 渲染**：依赖终端宽度自适应，非 TTY 环境（如 Jupyter、CI）需传 `--disable-ui`
- **`.temp` 文件**：下载中断会保留 `.temp` 后缀的临时文件，不会自动清理
- **每次运行 `main.py`** 会在 `Backups/` 目录生成带时间戳的 `URLs_*.bak` 备份，处理完后清空 `URLs.txt`
- **域名 fallback**：`downloads` 子域被 403 拦截时自动切换为 `bunkr.cr` 重试（`general_utils.py` 的 `fetch_page`）
- **Ruff 配置**：全规则启用（`select = ["ALL"]`），行长限制 88 字符
