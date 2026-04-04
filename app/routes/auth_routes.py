# -*- coding: utf-8 -*-
"""
认证相关路由：注册、登录、退出。
"""
from flask import Blueprint, request, session

from app.service import auth_service
from app.utils.response import fail, ok

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    """用户注册，请求体 JSON：username, password, nickname(可选)。"""
    try:
        body = request.get_json(silent=True) or {}
        username = (body.get("username") or "").strip()
        password = body.get("password") or ""
        nickname = (body.get("nickname") or "").strip() or None
        success, msg, uid = auth_service.register_user(username, password, nickname)
        if not success:
            return fail(400, msg)
        return ok({"user_id": uid}, msg=msg)
    except Exception as e:  # noqa: BLE001 毕设要求接口不崩溃，统一捕获
        return fail(500, f"注册失败：{e!s}")


@auth_bp.route("/login", methods=["POST"])
def login():
    """登录，成功后写入 session：user_id, username。"""
    try:
        body = request.get_json(silent=True) or {}
        username = (body.get("username") or "").strip()
        password = body.get("password") or ""
        success, msg, row = auth_service.verify_login(username, password)
        if not success:
            return fail(400, msg)
        session["user_id"] = row["id"]
        session["username"] = row["username"]
        return ok({"user_id": row["id"], "username": row["username"]}, msg=msg)
    except Exception as e:
        return fail(500, f"登录失败：{e!s}")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """清除 session。"""
    session.clear()
    return ok(msg="已退出登录")
