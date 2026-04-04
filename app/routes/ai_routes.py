# -*- coding: utf-8 -*-
"""
AI 分析报告路由。
"""
from flask import Blueprint, request

from app.dao import ai_report_dao
from app.service import ai_service
from app.utils.auth_helper import current_user_id, login_required
from app.utils.response import fail, ok
from app.utils.serialize import json_safe_row, json_safe_rows

ai_bp = Blueprint("ai", __name__)


@ai_bp.route("/analyze", methods=["POST"])
@login_required
def analyze():
    """触发本地模拟分析；JSON 可选 device_id。"""
    try:
        uid = current_user_id()
        body = request.get_json(silent=True) or {}
        did = body.get("device_id")
        if did is not None:
            did = int(did)
        okb, msg, rid = ai_service.run_local_demo_analysis(uid, did)
        if not okb:
            return fail(400, msg)
        return ok({"report_id": rid}, msg=msg)
    except Exception as e:
        return fail(500, f"分析失败：{e!s}")


@ai_bp.route("/reports", methods=["GET"])
@login_required
def list_reports():
    """报告列表。"""
    try:
        uid = current_user_id()
        rows = ai_report_dao.list_by_user(uid)
        return ok(json_safe_rows(rows))
    except Exception as e:
        return fail(500, f"查询失败：{e!s}")


@ai_bp.route("/reports/<int:report_id>", methods=["GET"])
@login_required
def report_detail(report_id):
    """报告详情。"""
    try:
        uid = current_user_id()
        row = ai_report_dao.find_by_id_for_user(report_id, uid)
        if not row:
            return fail(404, "报告不存在")
        p = row.get("chart_meta")
        if isinstance(p, str):
            import json

            try:
                row["chart_meta"] = json.loads(p)
            except json.JSONDecodeError:
                row["chart_meta"] = None
        return ok(json_safe_row(row))
    except Exception as e:
        return fail(500, f"查询失败：{e!s}")
