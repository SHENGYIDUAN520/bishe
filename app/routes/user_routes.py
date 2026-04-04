# -*- coding: utf-8 -*-
"""
用户资料路由（需登录）。
"""
from flask import Blueprint, session

from app.utils.auth_helper import login_required
from app.utils.response import ok

user_bp = Blueprint("user", __name__)


@user_bp.route("/profile", methods=["GET"])
@login_required
def profile():
    """返回当前登录用户基本信息（后续可联表扩展）。"""
    return ok(
        {
            "user_id": session.get("user_id"),
            "username": session.get("username"),
        }
    )
