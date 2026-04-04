# -*- coding: utf-8 -*-
"""
统一 API 响应格式：{"code": int, "msg": str, "data": any}
"""
from flask import jsonify


def ok(data=None, msg="操作成功"):
    """成功响应，HTTP 状态码仍为 200，业务码 code=0。"""
    return jsonify({"code": 0, "msg": msg, "data": data})


def fail(code, msg, data=None, http_status=200):
    """
    失败响应：默认 HTTP 200，通过 body 内 code 区分（便于前端统一处理）。
    若需严格 REST，可将 http_status 改为 400/401 等。
    """
    return jsonify({"code": code, "msg": msg, "data": data}), http_status
