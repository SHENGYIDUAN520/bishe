# -*- coding: utf-8 -*-
"""
用户表数据访问：仅包含 SQL，不做业务判断。
"""
from app.db import get_cursor


def find_by_username(username):
    """按用户名查询单条用户记录。"""
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, username, password_hash, nickname, status FROM `user` WHERE username = %s LIMIT 1",
            (username,),
        )
        return cur.fetchone()


def insert_user(username, password_hash, nickname=None):
    """插入新用户，返回新记录主键。"""
    nick = nickname or username
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO `user` (username, password_hash, nickname, status)
            VALUES (%s, %s, %s, 1)
            """,
            (username, password_hash, nick),
        )
        return cur.lastrowid
