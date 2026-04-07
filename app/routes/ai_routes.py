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
    """触发 AI 分析并入库。

    JSON 可选字段：
    - device_id：可选，指定目标设备（不填则默认第一台）
    - environment_type：可选，取值：machine_room/home/factory/custom（或对应中文）
    - custom_context：可选，仅当 environment_type=custom 时生效
    """
    try:
        uid = current_user_id()
        body = request.get_json(silent=True) or {}
        did = body.get("device_id")
        if did is not None:
            did = int(did)

        env_raw = body.get("environment_type", "") or ""
        env = str(env_raw).strip()
        env_lower = env.lower()
        if env_lower in {"machine_room", "machineroom", "机房"}:
            env = "machine_room"
        elif env_lower in {"home", "普通家庭", "家庭", "residential"}:
            env = "home"
        elif env_lower in {"factory", "工厂", "plant"}:
            env = "factory"
        elif env_lower in {"custom", "自定义"}:
            env = "custom"
        else:
            # 默认按普通家庭处理
            env = "home"

        custom_context = (body.get("custom_context") or "").strip() or None
        if env != "custom":
            custom_context = None
        elif not custom_context:
            return fail(400, "自定义环境 environment_type=custom 时必须提供 custom_context")

        okb, msg, rid = ai_service.run_local_demo_analysis(
            uid, did, environment_type=env, custom_context=custom_context
        )
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


@ai_bp.route("/reports/<int:report_id>", methods=["DELETE"])
@login_required
def delete_report(report_id):
    """删除报告（仅允许删除属于当前用户的记录）。"""
    try:
        uid = current_user_id()
        okb = ai_report_dao.delete_for_user(uid, report_id)
        if not okb:
            return fail(404, "报告不存在")
        return ok(None, msg="删除成功")
    except Exception as e:
        return fail(500, f"删除失败：{e!s}")


@ai_bp.route("/temperature-advice", methods=["POST"])
@login_required
def temperature_advice():
    """返回温度告警的 AI 建议文本。"""
    try:
        body = request.get_json(silent=True) or {}
        t = float(body.get("temperature"))
        threshold = float(body.get("threshold"))
        h_raw = body.get("humidity")
        h = float(h_raw) if h_raw not in (None, "") else None
        txt = ai_service.generate_temp_alert_advice(t, h, threshold)
        return ok({"advice": txt})
    except ValueError:
        return fail(400, "temperature/threshold 必须为数字")
    except Exception as e:
        return fail(500, f"生成建议失败：{e!s}")
