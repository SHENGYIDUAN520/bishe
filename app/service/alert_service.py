# -*- coding: utf-8 -*-
"""
温度告警服务：超阈值邮件通知 + AI 建议。
"""
import smtplib
import ssl
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr, parseaddr
from typing import Optional
import re

from flask import current_app

from app.dao import device_setting_dao

# 简单进程内限流，避免高频刷邮件
_LAST_SENT_AT = {}
_LAST_ALERT_STATUS = {}


def _normalize_email_ascii(raw: str) -> str:
    """尽量把常见全角/脏字符邮箱归一化为 ASCII。"""
    s = (raw or "").strip()
    # 常见全角符号转半角
    s = (
        s.replace("＠", "@")
        .replace("。", ".")
        .replace("．", ".")
        .replace("－", "-")
        .replace("＿", "_")
    )
    # 清理所有空白（含全角空格/不可见空白）
    s = re.sub(r"\s+", "", s, flags=re.UNICODE)
    # 仅保留邮箱常见 ASCII 字符
    s = "".join(ch for ch in s if ch.isascii() and (ch.isalnum() or ch in "@._%+-"))
    return s


def _send_email(to_email: str, subject: str, body: str):
    cfg = current_app.config
    host = (cfg.get("SMTP_HOST") or "").strip()
    port = int(cfg.get("SMTP_PORT") or 0)
    user = (cfg.get("SMTP_USER") or "").strip()
    password = (cfg.get("SMTP_PASSWORD") or "").strip()
    sender = (cfg.get("SMTP_SENDER") or user).strip()
    use_ssl = bool(cfg.get("SMTP_SSL", True))

    if not host or not port or not user or not password or not sender:
        return False, "SMTP 配置不完整"

    # 规范化地址：sendmail 的 envelope 地址必须是纯邮箱（ASCII）
    sender_addr_raw = parseaddr(sender)[1].strip() or sender.strip()
    to_addr_raw = parseaddr(to_email)[1].strip() or to_email.strip()
    sender_addr = _normalize_email_ascii(sender_addr_raw)
    to_addr = _normalize_email_ascii(to_addr_raw)
    if "@" not in sender_addr:
        return (
            False,
            f"发件人邮箱格式无效（原始: {sender_addr_raw} | 清洗后: {sender_addr}）",
        )
    if "@" not in to_addr:
        return (
            False,
            f"收件人邮箱格式无效（原始: {to_addr_raw} | 清洗后: {to_addr}）",
        )
    try:
        sender_addr.encode("ascii")
        to_addr.encode("ascii")
    except UnicodeEncodeError:
        return False, "收件人或发件人邮箱包含非 ASCII 字符，请仅填写标准邮箱地址"

    msg = MIMEText(body, _subtype="plain", _charset="utf-8")
    msg["Subject"] = str(Header(subject, "utf-8"))
    # 兼容中文发件人显示名；若 sender 不是邮箱地址，SMTP 服务器可能拒收
    msg["From"] = formataddr((str(Header("物联网监控系统", "utf-8")), sender_addr))
    msg["To"] = to_addr

    if use_ssl:
        ctx = ssl.create_default_context()
        try:
            with smtplib.SMTP_SSL(host, port, context=ctx, timeout=10) as s:
                s.login(user, password)
                s.sendmail(sender_addr, [to_addr], msg.as_string())
            return True, "邮件发送成功"
        except Exception as e:
            return False, f"{type(e).__name__}: {e!s}"

    try:
        with smtplib.SMTP(host, port, timeout=10) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(user, password)
            s.sendmail(sender_addr, [to_addr], msg.as_string())
        return True, "邮件发送成功"
    except Exception as e:
        return False, f"{type(e).__name__}: {e!s}"


def maybe_send_temp_alert(device_id: int, temp: Optional[float], humidity: Optional[float]) -> None:
    """若超过用户阈值则发邮件（冷却期内不重复发送）。"""
    if temp is None:
        return
    row = device_setting_dao.get_alert_contact_by_device(device_id)
    if not row:
        return

    user_id = int(row.get("user_id"))
    now = datetime.now()
    key = f"{user_id}:{device_id}"
    to_email = (row.get("email") or "").strip()
    threshold = row.get("temp_warn_high")
    if not to_email:
        _LAST_ALERT_STATUS[key] = {
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "skipped",
            "message": "未发送：个人中心未配置邮箱",
            "device_id": device_id,
            "temperature": float(temp),
            "threshold": float(threshold) if threshold is not None else None,
            "to_email": "",
        }
        return
    if threshold is None:
        _LAST_ALERT_STATUS[key] = {
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "skipped",
            "message": "未发送：未配置温度阈值",
            "device_id": device_id,
            "temperature": float(temp),
            "threshold": None,
            "to_email": to_email,
        }
        return

    try:
        th = float(threshold)
        t = float(temp)
    except (TypeError, ValueError):
        return
    if t <= th:
        _LAST_ALERT_STATUS[key] = {
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "skipped",
            "message": "未发送：温度未超过阈值",
            "device_id": device_id,
            "temperature": t,
            "threshold": th,
            "to_email": to_email,
        }
        return

    last = _LAST_SENT_AT.get(key)
    cooldown_minutes = int(current_app.config.get("TEMP_ALERT_COOLDOWN_MINUTES", 10))
    if last and now - last < timedelta(minutes=cooldown_minutes):
        _LAST_ALERT_STATUS[key] = {
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "cooldown",
            "message": f"告警冷却中（{cooldown_minutes} 分钟内不重复发送）",
            "device_id": device_id,
            "temperature": t,
            "threshold": th,
            "to_email": to_email,
        }
        return

    # 注意：该函数运行在 /api/device/data 上报链路中，必须尽量快速返回，
    # 这里使用本地规则建议，避免远程 AI 调用导致设备端 HTTP 超时（如 -11）。
    advice = (
        f"当前温度 {t:.1f}℃ 已超过阈值 {th:.1f}℃。"
        "建议优先检查传感器与接线、通风散热、设备负载与供电稳定性。"
    )
    subject = f"[物联网平台] 温度告警：{row.get('device_name') or row.get('device_uid')}"
    body = (
        f"时间：{now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"设备：{row.get('device_name') or '未命名设备'} ({row.get('device_uid')})\n"
        f"当前温度：{t:.2f}℃\n"
    )
    if humidity is not None:
        try:
            body += f"当前湿度：{float(humidity):.2f}%RH\n"
        except (TypeError, ValueError):
            pass
    body += f"告警阈值：{th:.2f}℃\n\nAI 建议：\n{advice}\n"

    sent, detail = _send_email(to_email, subject, body)
    if sent:
        _LAST_SENT_AT[key] = now
        _LAST_ALERT_STATUS[key] = {
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "sent",
            "message": detail,
            "device_id": device_id,
            "temperature": t,
            "threshold": th,
            "to_email": to_email,
        }
    else:
        _LAST_ALERT_STATUS[key] = {
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "failed",
            "message": f"邮件发送失败：{detail}",
            "device_id": device_id,
            "temperature": t,
            "threshold": th,
            "to_email": to_email,
        }


def get_last_alert_status(user_id: int, device_id: int):
    """读取最近一次该用户该设备的告警邮件状态。"""
    key = f"{int(user_id)}:{int(device_id)}"
    return _LAST_ALERT_STATUS.get(key)

