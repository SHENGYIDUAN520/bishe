# -*- coding: utf-8 -*-
"""
应用入口：开发环境直接运行本文件启动 Flask 服务。
"""
import os

from dotenv import load_dotenv

# 优先加载项目根目录 .env
load_dotenv()

from app import create_app

app = create_app()

if __name__ == "__main__":
    # debug 仅用于本地开发，生产请使用 gunicorn 等 WSGI 服务器
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
