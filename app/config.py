# -*- coding: utf-8 -*-
"""
全局配置：从环境变量读取，避免密钥写死在代码中。
"""
import os


class Config:
    """Flask 配置类。"""

    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-only-change-me"
    # 开发阶段可设为 *；生产应配置为具体前端域名
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

    MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "iot_platform")

    # 火山方舟（OpenAI 兼容）：密钥与接入点 ID 仅来自环境变量，禁止写死在代码中
    AI_API_KEY = (os.environ.get("AI_API_KEY") or "").strip()
    AI_MODEL = (os.environ.get("AI_MODEL") or "").strip()
    ARK_BASE_URL = (
        os.environ.get("ARK_BASE_URL") or "https://ark.cn-beijing.volces.com/api/v3"
    ).strip()
