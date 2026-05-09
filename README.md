# Bunkr Downloader

> A Python Bunkr downloader that fetches images and videos from URLs. It supports both Bunkr albums and individual file URLs, logs issues, and enables concurrent downloads for efficiency.

![Demo](https://github.com/Lysagxra/BunkrDownloader/blob/8d07aaa4fe4e5b438e9ccc75bf0b71c845df942d/assets/demo.gif)

## Features

- Downloads multiple files from an album concurrently.
- Supports [batch downloading](https://github.com/Lysagxra/BunkrDownloader?tab=readme-ov-file#batch-download) via a list of URLs.
- Supports [selective files downloading](https://github.com/Lysagxra/BunkrDownloader/tree/main?tab=readme-ov-file#selective-download) based on filename criteria.
- Supports [custom download location](https://github.com/Lysagxra/BunkrDownloader/tree/main?tab=readme-ov-file#file-download-location).
- Provides [minimal UI](https://github.com/Lysagxra/BunkrDownloader/tree/main?tab=readme-ov-file#disable-ui-for-notebooks) for notebook environments.
- Provides progress indication during downloads.
- Automatically creates a directory structure for organized storage.
- Logs URLs that encounter errors for troubleshooting.
- Web URL 解析器，通过浏览器解析 Bunkr 链接并获取真实下载地址。
- 解析结果自动存入 PostgreSQL 数据库，支持历史记录查询、分页、模糊搜索。
- URL 去重：已成功解析的 URL 不会重复保存。

## Dependencies

- Python 3
- `BeautifulSoup` (bs4) - for HTML parsing
- `requests` - for HTTP requests
- `rich` - for progress display in the terminal
- `Flask` - for the web resolver server
- `psycopg2-binary` - for PostgreSQL database connection
- `cryptography` - for database password encryption

<details>

<summary>Show directory structure</summary>

```
project-root/
├── src/
│ ├── crawlers/
| | ├── api_utils.py         # Utilities for handling API requests and responses
│ │ └── crawler_utils.py     # Utilities for extracting media download links
│ ├── downloaders/
│ │ ├── album_downloader.py  # Manages the downloading of entire albums
│ │ ├── download_utils.py    # Utilities for managing the download process
│ │ └── media_downloader.py  # Manages the downloading of individual media files
│ ├── managers/
│ │ ├── live_manager.py      # Manages a real-time live display
│ │ ├── log_manager.py       # Manages real-time log updates
│ │ ├── progress_manager.py  # Manages progress bars
│ │ └── summary_manager.py   # Manages final summaries
│ ├── bunkr_utils.py         # Utilities for checking Bunkr status
│ ├── config.py              # Manages constants and settings used across the project
│ ├── crypto_utils.py        # Database password Fernet encryption/decryption
│ ├── database.py            # PostgreSQL connection pool and CRUD operations
│ ├── file_utils.py          # Utilities for managing file operations
│ ├── general_utils.py       # Miscellaneous utility functions
│ └── url_utils.py           # Utilities for Bunkr URLs
├── templates/
│ ├── index.html             # Web resolver main page (SSE-driven single page app)
│ └── history.html           # History query page with search and pagination
├── scripts/
│ └── encrypt_password.py    # CLI tool to encrypt database password for deployment
├── db_code/
│ └── init_postgres.sql      # PostgreSQL DDL reference script
├── downloader.py            # Module for initiating downloads from specified Bunkr URLs
├── main.py                  # Main script to run the downloader
├── server.py                # Flask web server with SSE streaming and DB integration
├── URLs.txt                 # Text file listing album URLs to be downloaded
└── session_log.txt          # Log file for recording session details
```

</details>

## Installation

1. Clone the repository:

```bash
git clone https://github.com/Lysagxra/BunkrDownloader.git
```

2. Navigate to the project directory:

```bash
cd BunkrDownloader
```

3. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Single Download

To download a single media from an URL, you can use `downloader.py`, running the script with a valid album or media URL.

### Usage

```bash
python3 downloader.py <bunkr_url>
```

### Examples

You can either download an entire album or a specific file:

```
python3 downloader.py https://bunkr.si/a/PUK068QE       # Download album
python3 downloader.py https://bunkr.fi/f/gBrv5f8tAGlGW  # Download single media
```

## Selective Download

The script supports selective file downloads from an album, allowing you to exclude files using the [Ignore List](https://github.com/Lysagxra/BunkrDownloader?tab=readme-ov-file#ignore-list) and include specific files with the [Include List](https://github.com/Lysagxra/BunkrDownloader?tab=readme-ov-file#include-list).

## Ignore List

The Ignore List is specified using the `--ignore` argument in the command line.
This allows you to skip the download of any file from an album if its filename contains at least one of the specified strings in the list.
Item in the list should be separated by a space.

### Usage

```bash
python3 downloader.py <bunkr_album_url> --ignore <ignore_list>
```

### Example

This feature is particularly useful when you want to skip files with certain extensions, such as `.zip` files. For instance:

```bash
python3 downloader.py https://bunkr.si/a/xxxxxx --ignore .zip
```

## Include List

The Include List is specified using the `--include` argument in the command line.
This allows you to download a file from an album only if its filename contains at least one of the specified strings in the list.
Items in the list should be separated by a space.

### Usage

```bash
python3 downloader.py <bunkr_album_url> --include <include_list>
```

### Example

```bash
python3 downloader.py https://bunkr.si/a/xxxxxxxx --include FullSizeRender
```

## Batch Download

To batch download from multiple URLs, you can use the `main.py` script.
This script reads URLs from a file named `URLs.txt` and downloads each one using the media downloader.

### Usage

1. Create a file named `URLs.txt` in the root of your project, listing each URL on a new line.

- Example of `URLs.txt`:

```
https://bunkr.si/a/xxxx
https://bunkr.fi/f/yyyy
https://bunkr.fi/a/zzzz
```

- Ensure that each URL is on its own line without any extra spaces.
- You can add as many URLs as you need, following the same format.

2. Run the batch download script:

```
python3 main.py
```

## File Download Location

If the `--custom-path <custom_path>` argument is used, the downloaded files will be saved in `<custom_path>/Downloads`.
Otherwise, the files will be saved in a `Downloads` folder created within the script's directory

### Usage

```bash
python3 main.py --custom-path <custom_path>
```

### Example

```bash
python3 main.py --custom-path /path/to/external/drive
```

## Disable UI for Notebooks

When the script is executed in a notebook environment (such as Jupyter), excessive output may lead to performance issues or crashes.

### Usage

You can run the script with the `--disable-ui` argument to disable the progress bar and minimize log messages.

To disable the UI, use the following command:

```
python3 main.py --disable-ui
```

To download a single file or album without the UI, you can use this command:

```bash
python3 downloader.py <bunkr_url> --disable-ui
```

## Maximum Number of Retries

When the download fails, by default there is 5 retry attempts to download each media file again.
You can control the number of maximum attempts with the `--max-retries` argument.
It may be useful when you would like to skip broken media faster for the very large media collection.

### Usage

Allowed values: 0 (don't re-download) and larger.

```bash
python3 downloader.py <bunkr_url> --max-retries 3
```

### Example:

```bash
python3 downloader.py https://bunkr.si/a/xxxxxxx --max-retries 3
```

## Logging

The application logs any issues encountered during the download process in a file named `session.log`.
Check this file for any URLs that may have been blocked or had errors.

## Web 解析器

启动 Flask Web 服务器，在浏览器中粘贴 Bunkr URL 即可获取真实下载地址。

### 启动

```bash
# 前台启动（开发调试）
python server.py
# 浏览器打开 http://127.0.0.1:5000
```

### 数据库配置

解析结果自动保存到 PostgreSQL 数据库，需先配置加密密钥。

```bash
# 1. 生成加密密钥
python scripts/encrypt_password.py

# 2. 将输出的 export 命令写入 ~/.zshrc
export BUNKR_DB_KEY='<生成密钥>'
export BUNKR_DB_PASSWORD_ENC='<加密后的密码>'
source ~/.zshrc

# 3. 在 PostgreSQL 中创建数据库
# psql -h <your_database_host_ip> -p 5243 -U <your_database_username> -c "CREATE DATABASE bunkr_downloader;"

# 4. 启动（表结构自动创建，数据库不可用时自动降级运行）
python server.py
```

### 后台运行

```bash
# 后台启动（需先加载环境变量）
source ~/.zshrc && nohup env BUNKR_DB_KEY="$BUNKR_DB_KEY" BUNKR_DB_PASSWORD_ENC="$BUNKR_DB_PASSWORD_ENC" .venv/bin/python server.py > /dev/null 2>&1 &

# 停止后台服务
lsof -i :5000
kill -9 <PID>
```

### 功能说明

| 功能 | 说明 |
|---|---|
| URL 解析 | 支持专辑（/a/）和单文件（/f/ /i/ /v/），SSE 实时推送进度 |
| 操作按钮 | 每条结果支持 Motrix 下载、复制地址、直接下载、标记完成 |
| 历史记录 | 点击"历史记录查询"在新标签页打开，支持分页、文件名模糊搜索、时间降序 |
| 记录管理 | 支持单条删除和清空所有记录 |
| URL 去重 | 已成功解析的 URL 不会重复保存 |
| 降级运行 | 数据库连接失败时，解析功能不受影响，仅数据库功能不可用 |