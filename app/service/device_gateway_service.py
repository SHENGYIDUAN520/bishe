# -*- coding: utf-8 -*-
"""
设备网关业务：注册、鉴权、心跳、上报、拉指令、回执。
"""
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.dao import command_dao, device_dao, device_data_dao


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def register_or_login(
    device_uid: str,
    device_secret: Optional[str],
    firmware_ver: Optional[str],
    name: Optional[str],
) -> Tuple[bool, str, Optional[Dict]]:
    """设备注册/重复注册校验。"""
    uid = (device_uid or "").strip()
    if not uid:
        return False, "缺少 device_uid", None
    sec = (device_secret or "").strip()
    row = device_dao.find_by_uid(uid)
    if row:
        if sec and row.get("device_secret") != sec:
            return False, "设备密钥不匹配", None
        if firmware_ver:
            device_dao.update_firmware(int(row["id"]), firmware_ver.strip())
        device_dao.touch_heartbeat(int(row["id"]))
        return True, "设备已存在，校验通过", {
            "device_id": int(row["id"]),
            "device_uid": uid,
            "device_secret": row.get("device_secret"),
        }

    # 首次注册：若未提供密钥则服务端生成
    final_secret = sec or secrets.token_urlsafe(16)
    device_id = device_dao.insert_device(
        device_uid=uid,
        device_secret=final_secret,
        user_id=None,
        name=(name or f"设备-{uid}").strip(),
        firmware_ver=(firmware_ver or "").strip() or None,
    )
    device_dao.touch_heartbeat(device_id)
    return True, "注册成功", {
        "device_id": device_id,
        "device_uid": uid,
        "device_secret": final_secret,
    }


def verify_device(device_uid: str, device_secret: str) -> Tuple[bool, str, Optional[Dict]]:
    """设备身份校验。"""
    uid = (device_uid or "").strip()
    sec = (device_secret or "").strip()
    if not uid or not sec:
        return False, "缺少 device_uid 或 device_secret", None
    row = device_dao.find_by_uid(uid)
    if not row:
        return False, "设备不存在", None
    if row.get("device_secret") != sec:
        return False, "设备鉴权失败", None
    return True, "ok", row


def heartbeat(device_uid: str, device_secret: str) -> Tuple[bool, str]:
    """心跳上报。"""
    ok, msg, row = verify_device(device_uid, device_secret)
    if not ok:
        return False, msg
    device_dao.touch_heartbeat(int(row["id"]))
    return True, "心跳已更新"


def upload_data(device_uid: str, device_secret: str, payload: Any) -> Tuple[bool, str, int]:
    """
    上传数据：支持单条对象或数组。
    对象字段：temperature, humidity, illuminance, recorded_at(可选)
    """
    ok, msg, row = verify_device(device_uid, device_secret)
    if not ok:
        return False, msg, 0
    device_id = int(row["id"])
    items: List[Dict[str, Any]]
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = [payload]
    else:
        return False, "payload 类型错误，应为对象或数组", 0

    cnt = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        recorded_at = (it.get("recorded_at") or "").strip() or _now_str()
        device_data_dao.insert_row(
            device_id=device_id,
            temperature=it.get("temperature"),
            humidity=it.get("humidity"),
            illuminance=it.get("illuminance"),
            recorded_at=recorded_at,
        )
        cnt += 1
    device_dao.touch_heartbeat(device_id)
    return True, f"已写入 {cnt} 条数据", cnt


def poll_command(device_uid: str, device_secret: str) -> Tuple[bool, str, Optional[Dict]]:
    """拉取下一条待执行指令。"""
    ok, msg, row = verify_device(device_uid, device_secret)
    if not ok:
        return False, msg, None
    cmd = command_dao.fetch_next_pending(int(row["id"]))
    if not cmd:
        return True, "暂无待执行指令", None
    return True, "ok", cmd


def ack_command(
    device_uid: str,
    device_secret: str,
    command_id: int,
    success: bool,
    result_msg: str,
) -> Tuple[bool, str]:
    """回执指令结果。"""
    ok, msg, row = verify_device(device_uid, device_secret)
    if not ok:
        return False, msg
    updated = command_dao.mark_command_result(
        int(row["id"]), int(command_id), bool(success), (result_msg or "").strip()[:500]
    )
    if not updated:
        return False, "指令不存在或不属于该设备"
    return True, "回执已记录"
