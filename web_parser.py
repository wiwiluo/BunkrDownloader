from flask import Flask, render_template, request, jsonify
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.crawlers.crawler_utils import (
    extract_all_album_item_pages,
    get_download_info,
)
from src.general_utils import fetch_page
from src.url_utils import (
    check_url_type,
    get_host_page,
    get_identifier,
)

app = Flask(__name__)

async def parse_bunkr_url(url):
    """解析Bunkr URL并提取真实下载链接"""
    try:
        # 获取页面内容
        initial_soup = await fetch_page(url)
        if not initial_soup:
            return {"error": "无法获取页面内容"}

        host_page = get_host_page(url)
        identifier = get_identifier(url, soup=initial_soup)

        download_info_list = []

        # 判断是专辑还是单个文件
        if check_url_type(url):
            # 专辑URL
            item_pages = await extract_all_album_item_pages(initial_soup, host_page, url)
            
            # 遍历所有项目页面，提取下载信息
            for item_url in item_pages:
                item_soup = await fetch_page(item_url)
                if item_soup:
                    download_link, filename = await get_download_info(item_url, item_soup)
                    if download_link and filename:
                        download_info_list.append({
                            "filename": filename,
                            "download_link": download_link
                        })
        else:
            # 单个文件URL
            download_link, filename = await get_download_info(url, initial_soup)
            if download_link and filename:
                download_info_list.append({
                    "filename": filename,
                    "download_link": download_link
                })

        return {"download_info_list": download_info_list}
    
    except Exception as e:
        return {"error": f"解析过程中出现错误: {str(e)}"}

@app.route('/')
def index():
    return render_template('parser.html')

@app.route('/parse', methods=['POST'])
def parse_url():
    url = request.form.get('url')
    if not url:
        return jsonify({"error": "URL不能为空"})
    
    # 运行异步函数
    result = asyncio.run(parse_bunkr_url(url))
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)