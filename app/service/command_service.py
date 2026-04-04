# -*- coding: utf-8 -*-
"""
远程指令业务：写入待下发记录（硬件上线后由网关拉取执行）。
"""
from typing import Any, Dict, List, Optional, Tuple

from app.dao import command_dao
from app.service import device_service

# 毕设演示用指令类型白名单
ALLOWED_TYPES = frozenset({"reboot", "set_interval", "sensor_on", "sensor_off"})


def enqueue(user_id: int, device_id: int, command_type: str, payload: Optional[Dict]) -> Tuple[bool, str, Optional[int]]:
    """创建一条 pending 指令。"""
    if not device_service.assert_owned(user_id, device_id):
        return False, "设备不存在或无权操作", None
    ct = (command_type or "").strip()
    if ct not in ALLOWED_TYPES:
        return False, f"不支持的指令类型，可选：{', '.join(sorted(ALLOWED_TYPES))}", None
    cid = command_dao.insert_command(device_id, ct, payload)
    return True, "指令已记录，待设备拉取执行", cid


def list_for_device(user_id: int, device_id: int) -> Tuple[bool, str, List[Dict]]:
    """指令历史。"""
    if not device_service.assert_owned(user_id, device_id):
        return False, "设备不存在或无权查看", []
    rows = command_dao.list_by_device(device_id)
    return True, "ok", rows
