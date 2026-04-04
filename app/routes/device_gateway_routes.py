# -*- coding: utf-8 -*-
"""
设备网关接口：供 ESP32 调用，使用 device_uid + device_secret 鉴权（后续在 service 校验）。
"""
from flask import Blueprint, request

from app.utils.response import fail, ok

device_gateway_bp = Blueprint("device_gateway", __name__)


def _device_body():
    """解析 JSON 请求体。"""
    return request.get_json(silent=True) or {}


@device_gateway_bp.route("/register", methods=["POST"])
def device_register():
    """设备首次向平台注册（占位）。"""
    return ok(None, msg="设备注册待实现")


@device_gateway_bp.route("/heartbeat", methods=["POST"])
def device_heartbeat():
    """心跳上报（占位）。"""
    return ok(None, msg="心跳接口待实现")


@device_gateway_bp.route("/data", methods=["POST"])
def device_upload_data():
    """传感数据上传，支持批量（占位）。"""
    _ = _device_body()
    return ok(None, msg="数据上传待实现")


@device_gateway_bp.route("/command", methods=["GET"])
def device_poll_command():
    """设备轮询待执行指令（占位）。"""
    device_uid = request.args.get("device_uid")
    if not device_uid:
        return fail(400, "缺少 device_uid")
    return ok(None, msg="拉取指令待实现")


@device_gateway_bp.route("/command/ack", methods=["POST"])
def device_command_ack():
    """指令执行结果回执（占位）。"""
    return ok(None, msg="回执接口待实现")
