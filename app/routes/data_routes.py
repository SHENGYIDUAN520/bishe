# -*- coding: utf-8 -*-
"""
设备数据查询路由。
"""
from flask import Blueprint, request

from app.service import data_service
from app.utils.auth_helper import current_user_id, login_required
from app.utils.response import fail, ok
from app.utils.serialize import json_safe_row, json_safe_rows

data_bp = Blueprint("data", __name__)


@data_bp.route("/devices/<int:device_id>/latest", methods=["GET"])
@login_required
def latest_data(device_id):
    """最新一条传感数据。"""
    try:
        uid = current_user_id()
        okb, msg, row = data_service.latest(uid, device_id)
        if not okb:
            return fail(403, msg)
        return ok({"device_id": device_id, "payload": json_safe_row(row)})
    except Exception as e:
        return fail(500, f"查询失败：{e!s}")


@data_bp.route("/devices/<int:device_id>/history", methods=["GET"])
@login_required
def history_data(device_id):
    """历史数据：Query start, end, page, page_size。"""
    try:
        uid = current_user_id()
        start = request.args.get("start") or None
        end = request.args.get("end") or None
        page = int(request.args.get("page") or 1)
        page_size = int(request.args.get("page_size") or 50)
        okb, msg, pack = data_service.history(uid, device_id, start, end, page, page_size)
        if not okb:
            return fail(403, msg)
        pack["list"] = json_safe_rows(pack["list"])
        return ok(pack)
    except ValueError:
        return fail(400, "分页参数必须为数字")
    except Exception as e:
        return fail(500, f"查询失败：{e!s}")
