# -*- coding: utf-8 -*-
"""设备网关接口：供 ESP32 调用。"""
from flask import Blueprint, request

from app.service import device_gateway_service
from app.utils.response import fail, ok

device_gateway_bp = Blueprint("device_gateway", __name__)


def _device_body():
    """解析 JSON 请求体。"""
    return request.get_json(silent=True) or {}


@device_gateway_bp.route("/register", methods=["POST"])
def device_register():
    """设备注册/重复注册。"""
    try:
        body = _device_body()
        okb, msg, data = device_gateway_service.register_or_login(
            body.get("device_uid", ""),
            body.get("device_secret"),
            body.get("firmware_ver"),
            body.get("name"),
        )
        if not okb:
            return fail(400, msg)
        return ok(data, msg=msg)
    except Exception as e:
        return fail(500, f"设备注册失败：{e!s}")


@device_gateway_bp.route("/heartbeat", methods=["POST"])
def device_heartbeat():
    """心跳上报。"""
    try:
        body = _device_body()
        okb, msg = device_gateway_service.heartbeat(
            body.get("device_uid", ""),
            body.get("device_secret", ""),
        )
        if not okb:
            return fail(403, msg)
        return ok(None, msg=msg)
    except Exception as e:
        return fail(500, f"心跳失败：{e!s}")


@device_gateway_bp.route("/data", methods=["POST"])
def device_upload_data():
    """传感数据上传：支持 payload 单条对象或数组。"""
    try:
        body = _device_body()
        okb, msg, count = device_gateway_service.upload_data(
            body.get("device_uid", ""),
            body.get("device_secret", ""),
            body.get("payload"),
        )
        if not okb:
            return fail(403, msg)
        return ok({"count": count}, msg=msg)
    except Exception as e:
        return fail(500, f"上传失败：{e!s}")


@device_gateway_bp.route("/command", methods=["GET"])
def device_poll_command():
    """设备轮询待执行指令。"""
    device_secret = request.args.get("device_secret")
    device_uid = request.args.get("device_uid")
    if not device_uid or not device_secret:
        return fail(400, "缺少 device_uid 或 device_secret")
    try:
        okb, msg, cmd = device_gateway_service.poll_command(device_uid, device_secret)
        if not okb:
            return fail(403, msg)
        return ok(cmd, msg=msg)
    except Exception as e:
        return fail(500, f"拉取指令失败：{e!s}")


@device_gateway_bp.route("/command/ack", methods=["POST"])
def device_command_ack():
    """指令执行结果回执。"""
    try:
        body = _device_body()
        command_id = int(body.get("command_id") or 0)
        if command_id <= 0:
            return fail(400, "command_id 无效")
        okb, msg = device_gateway_service.ack_command(
            body.get("device_uid", ""),
            body.get("device_secret", ""),
            command_id=command_id,
            success=bool(body.get("success", False)),
            result_msg=body.get("result_msg", ""),
        )
        if not okb:
            return fail(403, msg)
        return ok(None, msg=msg)
    except ValueError:
        return fail(400, "command_id 必须为数字")
    except Exception as e:
        return fail(500, f"回执失败：{e!s}")
