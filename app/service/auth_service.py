# -*- coding: utf-8 -*-
"""
用户认证业务：注册、登录校验与 session 写入。
"""
from werkzeug.security import check_password_hash, generate_password_hash

from app.dao import user_dao


def register_user(username, password, nickname=None):
    """
    注册新用户。
    :return: (success: bool, msg: str, user_id: int|None)
    """
    if not username or not password:
        return False, "用户名和密码不能为空", None
    if len(username) < 3 or len(password) < 6:
        return False, "用户名至少3位，密码至少6位", None
    if user_dao.find_by_username(username):
        return False, "用户名已存在", None
    pwd_hash = generate_password_hash(password)
    uid = user_dao.insert_user(username, pwd_hash, nickname)
    return True, "注册成功", uid


def verify_login(username, password):
    """
    校验登录。
    :return: (success, msg, user_dict|None)
    """
    row = user_dao.find_by_username(username)
    if not row:
        return False, "用户不存在", None
    if row.get("status") != 1:
        return False, "账号已禁用", None
    if not check_password_hash(row["password_hash"], password):
        return False, "密码错误", None
    return True, "登录成功", row
