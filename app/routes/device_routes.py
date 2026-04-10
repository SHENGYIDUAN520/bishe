# -*- coding: utf-8 -*-
"""
设备管理路由（Web 端）。
"""
from flask import Blueprint, request

from app.service import device_service
from app.utils.auth_helper import current_user_id, login_required
from app.utils.response import fail, ok
from app.utils.serialize import json_safe_rows

device_bp = Blueprint("devices", __name__)


@device_bp.route("", methods=["GET"])
@login_required
def list_devices():
    """当前用户设备列表。"""
    uid = current_user_id()
    rows = device_service.list_for_user(uid)
    return ok(json_safe_rows(rows))


@device_bp.route("/bind", methods=["POST"])
@login_required
def bind_device():
    """绑定：JSON device_uid, device_secret，可选 name。"""
    try:
        uid = current_user_id()
        body = request.get_json(silent=True) or {}
        okb, msg = device_service.bind_device(
            uid,
            body.get("device_uid", ""),
            body.get("device_secret", ""),
            (body.get("name") or "").strip() or None,
        )
        if not okb:
            return fail(400, msg)
        return ok(None, msg=msg)
    except Exception as e:
        return fail(500, f"绑定失败：{e!s}")


@device_bp.route("/demo", methods=["POST"])
@login_required
def create_demo():
    """生成一台绑定到当前用户的模拟设备（无硬件调试）。"""
    try:
        uid = current_user_id()
        okb, msg, data = device_service.create_demo_device(uid)
        if not okb:
            return fail(400, msg)
        return ok(data, msg=msg)
    except Exception as e:
        return fail(500, f"创建失败：{e!s}")


@device_bp.route("/<int:device_id>", methods=["PUT"])
@login_required
def update_device(device_id):
    """更新名称：JSON { name }。"""
    try:
        uid = current_user_id()
        body = request.get_json(silent=True) or {}
        okb, msg = device_service.update_name(uid, device_id, body.get("name", ""))
        if not okb:
            return fail(400, msg)
        return ok({"id": device_id}, msg=msg)
    except Exception as e:
        return fail(500, f"更新失败：{e!s}")


@device_bp.route("/<int:device_id>/alert-threshold", methods=["PUT"])
@login_required
def update_device_alert_threshold(device_id):
    """更新设备独立温度告警阈值：JSON { temp_warn_high }。"""
    try:
        uid = current_user_id()
        body = request.get_json(silent=True) or {}
        okb, msg = device_service.update_temp_warn_high(uid, device_id, body.get("temp_warn_high"))
        if not okb:
            return fail(400, msg)
        return ok({"id": device_id}, msg=msg)
    except Exception as e:
        return fail(500, f"更新失败：{e!s}")


@device_bp.route("/<int:device_id>", methods=["DELETE"])
@login_required
def delete_device(device_id):
    """删除设备。"""
    try:
        uid = current_user_id()
        okb, msg = device_service.remove_device(uid, device_id)
        if not okb:
            return fail(400, msg)
        return ok({"id": device_id}, msg=msg)
    except Exception as e:
        return fail(500, f"删除失败：{e!s}")
