# -*- coding: utf-8 -*-
"""
设备管理业务：绑定、归属校验、演示设备创建等。
"""
import secrets
from typing import Any, Dict, List, Optional, Tuple

from app.dao import device_dao, device_setting_dao


def assert_owned(user_id: int, device_id: int) -> Optional[Dict]:
    """
    校验设备是否属于当前用户。
    :return: 设备行（含 secret）或 None
    """
    row = device_dao.find_by_id(device_id)
    if not row or row.get("user_id") != user_id:
        return None
    return row


def list_for_user(user_id: int) -> List[Dict]:
    """用户设备列表（不含密钥）。"""
    rows = device_dao.list_by_user_id(user_id)
    dids = [int(r["id"]) for r in rows]
    setting_map = device_setting_dao.list_by_device_ids(dids)
    for r in rows:
        r["temp_warn_high"] = setting_map.get(int(r["id"]))
    return rows


def bind_device(user_id: int, device_uid: str, device_secret: str, name: Optional[str]) -> Tuple[bool, str]:
    """
    绑定未归属或校验密钥后归属到当前用户。
    毕设演示：明文比对 device_secret。
    """
    uid = (device_uid or "").strip()
    sec = (device_secret or "").strip()
    if not uid or not sec:
        return False, "请填写设备标识与密钥"
    row = device_dao.find_by_uid(uid)
    if not row:
        return False, "设备不存在，请确认已先在平台注册或由管理员录入"
    if row.get("device_secret") != sec:
        return False, "设备密钥错误"
    other = row.get("user_id")
    if other is not None and int(other) != int(user_id):
        return False, "该设备已绑定其他账号"
    if int(other or 0) == int(user_id):
        return True, "该设备已绑定到当前账号"
    device_dao.bind_to_user(int(row["id"]), user_id, name or row.get("name") or uid)
    return True, "绑定成功"


def update_name(user_id: int, device_id: int, name: str) -> Tuple[bool, str]:
    """修改设备名称。"""
    nm = (name or "").strip()
    if not nm:
        return False, "名称不能为空"
    if not assert_owned(user_id, device_id):
        return False, "设备不存在或无权操作"
    device_dao.update_device_name(device_id, nm)
    return True, "已保存"


def update_temp_warn_high(user_id: int, device_id: int, temp_warn_high) -> Tuple[bool, str]:
    """更新设备独立告警温度上限。"""
    if not assert_owned(user_id, device_id):
        return False, "设备不存在或无权操作"
    warn_val = None
    if temp_warn_high not in (None, ""):
        try:
            warn_val = float(temp_warn_high)
        except (TypeError, ValueError):
            return False, "温度阈值必须为数字"
        if warn_val < -50 or warn_val > 150:
            return False, "温度阈值范围应为 -50~150"
    device_setting_dao.upsert_temp_warn_high(device_id, warn_val)
    return True, "设备告警阈值已保存"


def remove_device(user_id: int, device_id: int) -> Tuple[bool, str]:
    """删除设备（级联删除数据与指令）。"""
    if not assert_owned(user_id, device_id):
        return False, "设备不存在或无权操作"
    device_dao.delete_device(device_id)
    return True, "已删除"


def create_demo_device(user_id: int) -> Tuple[bool, str, Optional[Dict]]:
    """
    无硬件时生成一台绑定到当前用户的模拟设备，便于联调页面。
    """
    suffix = secrets.token_hex(4).upper()
    d_uid = f"SIM-{suffix}"
    d_sec = secrets.token_urlsafe(12)
    nm = f"模拟设备-{suffix}"
    new_id = device_dao.insert_device(d_uid, d_sec, user_id, nm, "simulator")
    return True, "已创建模拟设备", {
        "id": new_id,
        "device_uid": d_uid,
        "device_secret": d_sec,
        "name": nm,
        "hint": "密钥仅本次展示，请自行保存；页面刷新后需到数据库查看或再生成一台",
    }
