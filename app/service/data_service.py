# -*- coding: utf-8 -*-
"""
设备数据查询业务。
"""
from typing import Any, Dict, List, Optional, Tuple

from app.dao import device_data_dao
from app.service import device_service


def latest(user_id: int, device_id: int) -> Tuple[bool, str, Optional[Dict]]:
    """最新一条数据。"""
    if not device_service.assert_owned(user_id, device_id):
        return False, "设备不存在或无权查看", None
    row = device_data_dao.latest_by_device(device_id)
    return True, "ok", row


def history(
    user_id: int,
    device_id: int,
    start: Optional[str],
    end: Optional[str],
    page: int,
    page_size: int,
) -> Tuple[bool, str, Optional[Dict]]:
    """分页历史。"""
    if not device_service.assert_owned(user_id, device_id):
        return False, "设备不存在或无权查看", None
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 200:
        page_size = 50
    rows, total = device_data_dao.history_by_device(device_id, start, end, page, page_size)
    return True, "ok", {"list": rows, "total": total, "page": page, "page_size": page_size}
