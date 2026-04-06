# -*- coding: utf-8 -*-
"""
指令日志表访问。
"""
import json
from typing import Any, Dict, List, Optional

from app.db import get_cursor


def insert_command(device_id: int, command_type: str, payload: Optional[Dict]) -> int:
    """写入一条待下发指令。"""
    payload_json = json.dumps(payload, ensure_ascii=False) if payload is not None else None
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO command_log (device_id, command_type, payload, status)
            VALUES (%s, %s, %s, 'pending')
            """,
            (device_id, command_type, payload_json),
        )
        return int(cur.lastrowid)


def list_by_device(device_id: int, limit: int = 50) -> List[Dict]:
    """最近指令记录。"""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, device_id, command_type, payload, status, result_msg, created_at, updated_at
            FROM command_log
            WHERE device_id = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (device_id, limit),
        )
        rows = list(cur.fetchall())
    for r in rows:
        p = r.get("payload")
        if isinstance(p, str):
            try:
                r["payload"] = json.loads(p)
            except json.JSONDecodeError:
                pass
    return rows


def fetch_next_pending(device_id: int) -> Optional[Dict]:
    """获取设备最早一条 pending 指令。"""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, device_id, command_type, payload, status, created_at
            FROM command_log
            WHERE device_id = %s AND status = 'pending'
            ORDER BY id ASC
            LIMIT 1
            """,
            (device_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    p = row.get("payload")
    if isinstance(p, str):
        try:
            row["payload"] = json.loads(p)
        except json.JSONDecodeError:
            pass
    return row


def mark_command_result(device_id: int, command_id: int, success: bool, result_msg: str) -> bool:
    """写入设备回执结果。"""
    new_status = "done" if success else "fail"
    with get_cursor(commit=True) as cur:
        affected = cur.execute(
            """
            UPDATE command_log
            SET status = %s, result_msg = %s
            WHERE id = %s AND device_id = %s
            """,
            (new_status, result_msg, command_id, device_id),
        )
        return affected > 0
