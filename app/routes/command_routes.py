# -*- coding: utf-8 -*-
"""
远程指令路由。
"""
from flask import Blueprint, request

from app.service import command_service
from app.utils.auth_helper import current_user_id, login_required
from app.utils.response import fail, ok
from app.utils.serialize import json_safe_rows

command_bp = Blueprint("command", __name__)


@command_bp.route("/devices/<int:device_id>/commands", methods=["POST"])
@login_required
def send_command(device_id):
    """下发指令：JSON command_type, payload(可选对象)。"""
    try:
        uid = current_user_id()
        body = request.get_json(silent=True) or {}
        ctype = body.get("command_type", "")
        payload = body.get("payload")
        if payload is not None and not isinstance(payload, dict):
            return fail(400, "payload 须为 JSON 对象")
        okb, msg, cid = command_service.enqueue(uid, device_id, ctype, payload)
        if not okb:
            return fail(400, msg)
        return ok({"id": cid, "device_id": device_id}, msg=msg)
    except Exception as e:
        return fail(500, f"下发失败：{e!s}")


@command_bp.route("/devices/<int:device_id>/commands", methods=["GET"])
@login_required
def list_commands(device_id):
    """指令历史。"""
    try:
        uid = current_user_id()
        okb, msg, rows = command_service.list_for_device(uid, device_id)
        if not okb:
            return fail(403, msg)
        return ok({"device_id": device_id, "list": json_safe_rows(rows)})
    except Exception as e:
        return fail(500, f"查询失败：{e!s}")
