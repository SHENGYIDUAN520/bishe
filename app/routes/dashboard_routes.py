# -*- coding: utf-8 -*-
"""
首页概览统计。
"""
from flask import Blueprint

from app.dao import device_dao
from app.utils.auth_helper import current_user_id, login_required
from app.utils.response import ok
from app.utils.serialize import json_safe_rows

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/overview", methods=["GET"])
@login_required
def overview():
    """当前用户设备数、今日数据量、设备简要列表。"""
    uid = current_user_id()
    devices = device_dao.list_by_user_id(uid)
    return ok(
        {
            "device_count": device_dao.count_by_user(uid),
            "today_data_count": device_dao.count_today_data_by_user(uid),
            "devices": json_safe_rows(devices),
        }
    )
