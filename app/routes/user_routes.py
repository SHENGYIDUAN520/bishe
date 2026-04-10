# -*- coding: utf-8 -*-
"""用户资料路由（需登录）。"""
from flask import Blueprint, request, session

from app.dao import user_dao
from app.service import alert_service, device_service
from app.utils.auth_helper import login_required
from app.utils.response import fail, ok
from app.utils.serialize import json_safe_row

user_bp = Blueprint("user", __name__)


@user_bp.route("/profile", methods=["GET"])
@login_required
def profile():
    """返回当前登录用户基本信息。"""
    uid = int(session.get("user_id"))
    row = user_dao.find_by_id(uid) or {}
    return ok(
        {
            "user_id": uid,
            "username": row.get("username") or session.get("username"),
            "nickname": row.get("nickname"),
            "email": row.get("email"),
            "phone": row.get("phone"),
        }
    )


@user_bp.route("/profile", methods=["PUT"])
@login_required
def update_profile():
    """更新邮箱、电话。"""
    try:
        uid = int(session.get("user_id"))
        body = request.get_json(silent=True) or {}
        email = (body.get("email") or "").strip()
        phone = (body.get("phone") or "").strip()

        if email and "@" not in email:
            return fail(400, "邮箱格式不正确")
        if phone and len(phone) > 20:
            return fail(400, "手机号长度不能超过 20")

        user_dao.update_contact(uid, email, phone)
        return ok(None, msg="保存成功")
    except Exception as e:
        return fail(500, f"保存失败：{e!s}")


@user_bp.route("/alert-status/<int:device_id>", methods=["GET"])
@login_required
def alert_status(device_id):
    """返回当前用户某设备最近一次告警邮件状态。"""
    uid = int(session.get("user_id"))
    if not device_service.assert_owned(uid, device_id):
        return fail(403, "设备不存在或无权查看")
    row = alert_service.get_last_alert_status(uid, device_id)
    return ok(json_safe_row(row))


@user_bp.route("/email-test", methods=["POST"])
@login_required
def email_test():
    """手动测试 SMTP 发信配置。"""
    try:
        uid = int(session.get("user_id"))
        user = user_dao.find_by_id(uid) or {}
        to_email = (user.get("email") or "").strip()
        if not to_email:
            return fail(400, "请先在个人中心设置邮箱")
        from datetime import datetime

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        okb, detail = alert_service._send_email(  # 仅测试用途
            to_email,
            "[物联网平台] SMTP 测试邮件",
            f"这是一封 SMTP 测试邮件。\n时间：{now}\n如果你收到，说明发信配置已生效。",
        )
        if not okb:
            return fail(400, f"测试发送失败：{detail}")
        return ok(None, msg="测试邮件发送成功，请检查收件箱")
    except Exception as e:
        return fail(500, f"测试失败：{e!s}")
