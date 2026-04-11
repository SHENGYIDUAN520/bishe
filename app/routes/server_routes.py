# -*- coding: utf-8 -*-
"""
本机服务发现：供蓝牙配网页在 127.0.0.1 打开时自动填写设备可访问的局域网 Base URL。
"""
import socket

from flask import Blueprint, request

from app.utils.response import ok

server_bp = Blueprint("server", __name__)


def _guess_lan_ipv4():
    """
    通过 UDP connect 取本机用于出网的 IPv4（通常为局域网网卡地址）。
    无网络或异常时退回 127.0.0.1（前端仍会校验，不建议作为设备 server_base）。
    """
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.35)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        if s is not None:
            try:
                s.close()
            except OSError:
                pass


def _host_port():
    h = request.host or ""
    if ":" in h:
        return h.rsplit(":", 1)[-1]
    return "5000"


@server_bp.route("/lan-hint", methods=["GET"])
def lan_hint():
    """
    返回建议的 server_base，形如 http://192.168.x.x:5000。
    无需登录；仅在内网演示使用。
    """
    ip = _guess_lan_ipv4()
    port = _host_port()
    base = "http://%s:%s" % (ip, port)
    return ok({"base": base, "ip": ip, "port": port})
