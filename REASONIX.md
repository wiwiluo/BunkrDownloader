# REASONIX.md — Bunkr Downloader

## 语言规范

请严格遵守以下规则：
1. 所有对话、解释、建议必须使用**简体中文**。
2. 代码注释必须使用中文。
3. 生成的 Commit Message 必须使用中文。
4. 严禁出现大段未翻译的英文技术名词（保留专业术语如 API、SDK 除外）。

## 技术栈

- **语言**: Python ≥ 3.10
- **beautifulsoup4** — HTML 解析
- **requests** — HTTP 客户端
- **rich** — 终端 UI（进度条、表格）
- **Flask** — Web 服务器（server.py）

## 目录结构

| 路径 | 说明 |
|---|---|
| `src/` | 主包：爬取/下载/UI 管理器 |
| `src/crawlers/` | 页面解析 + API 解密 |
| `src/downloaders/` | 文件下载 + 重试 + 进度 |
| `src/managers/` | Rich 实时 UI（进度/日志/汇总） |
| `downloader.py` | CLI 单 URL 下载入口 |
| `main.py` | 批量下载（从 URLs.txt 读取） |
| `server.py` | Flask Web 解析器 |
| `templates/` | Flask Jinja2 模板 |

## 命令

```bash
pip install -r requirements.txt

python main.py                   # 批量下载（URLs.txt）
python downloader.py <url>       # 单 URL 下载
python downloader.py <url> --help  # 查看参数

python server.py                 # 启动 Web 解析器 → http://127.0.0.1:5000
```

## CLI 参数（downloader.py）

| 参数 | 说明 |
|---|---|
| `url` | 必填，Bunkr 专辑或文件 URL |
| `--custom-path` | 指定下载目录 |
| `--no-download-folder` | 不在 Downloads 子文件夹内保存 |
| `--disable-ui` | 禁用 Rich UI（适合 notebook） |
| `--disable-disk-check` | 跳过磁盘空间检查 |
| `--max-retries N` | 最大重试次数（默认 5） |
| `--ignore` / `--include` | 按文件名过滤 |

## 代码规范

- **Ruff 检查**: `ruff check .`，行宽 88，启用 `ALL` 规则
- **CI**: GitHub Actions (pylint) 测试 Python 3.10 / 3.11
- **类型注解**: 全项目使用 PEP 484 类型提示
- **提交信息**: 50 字以内标题 + 正文（CONTRIBUTING.md）

## 注意事项

- **无测试文件** — 项目未配置任何测试框架
- **URL 解密** (`api_utils.py`) — 使用 XOR + 时间密钥 (`timestamp / 3600`)，Bunkr 修改 API 格式会直接失效
- **server.py 中 `asyncio.run()`** — Flask 开发服务器是同步的，所以能工作；切换到 ASGI 服务器会崩溃
- **Rich Live 渲染** — 依赖终端宽度自适应，非 TTY 环境需 `--disable-ui`
- **备份机制** — 每次运行 `main.py` 会在 `Backups/` 生成带时间戳的 URL 文件副本
- **`.temp` 文件** — 下载中断会保留 `.temp` 后缀文件，不自动清理