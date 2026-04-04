# -*- coding: utf-8 -*-
"""
登录态与权限校验：后续与 user 表、session 联动实现。
"""
from functools import wraps

from flask import session

from app.utils.response import fail


def login_required(fn):
    """
    装饰器：要求 session 中存在 user_id，否则返回 401。
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return fail(401, "请先登录", http_status=401)
        return fn(*args, **kwargs)

    return wrapper


def current_user_id():
    """获取当前登录用户主键，未登录返回 None。"""
    return session.get("user_id")
