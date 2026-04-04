# -*- coding: utf-8 -*-
"""
数据库连接：仅供 dao 层调用，避免在路由中直接使用 PyMySQL。
"""
from contextlib import contextmanager

import pymysql
from flask import current_app


def get_connection():
    """
    获取一条 MySQL 连接（字典游标，便于转 JSON）。
    调用方负责 close，或使用下方上下文管理器。
    """
    cfg = current_app.config
    return pymysql.connect(
        host=cfg["MYSQL_HOST"],
        port=cfg["MYSQL_PORT"],
        user=cfg["MYSQL_USER"],
        password=cfg["MYSQL_PASSWORD"],
        database=cfg["MYSQL_DATABASE"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


@contextmanager
def get_cursor(commit=False):
    """
    获取游标的上下文管理器，自动提交/回滚/关闭连接。

    :param commit: 为 True 时在退出成功路径执行 commit
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
