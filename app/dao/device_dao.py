# -*- coding: utf-8 -*-
"""
设备表数据访问。
"""
from typing import Any, Dict, List, Optional

from app.db import get_cursor


def list_by_user_id(user_id: int) -> List[Dict]:
    """某用户名下设备列表。"""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, device_uid, user_id, name, status, last_heartbeat, firmware_ver, created_at
            FROM device
            WHERE user_id = %s
            ORDER BY id DESC
            """,
            (user_id,),
        )
        return list(cur.fetchall())


def find_by_id(device_id: int) -> Optional[Dict]:
    """按主键查设备（不校验归属）。"""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, device_uid, device_secret, user_id, name, status, last_heartbeat, firmware_ver, created_at
            FROM device WHERE id = %s LIMIT 1
            """,
            (device_id,),
        )
        return cur.fetchone()


def find_by_uid(device_uid: str) -> Optional[Dict]:
    """按 device_uid 查询。"""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, device_uid, device_secret, user_id, name, status, last_heartbeat, firmware_ver, created_at
            FROM device WHERE device_uid = %s LIMIT 1
            """,
            (device_uid,),
        )
        return cur.fetchone()


def touch_heartbeat(device_id: int) -> None:
    """更新设备最后心跳时间。"""
    with get_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE device SET last_heartbeat = NOW() WHERE id = %s",
            (device_id,),
        )


def update_firmware(device_id: int, firmware_ver: str) -> None:
    """更新设备固件版本。"""
    with get_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE device SET firmware_ver = %s WHERE id = %s",
            (firmware_ver, device_id),
        )


def insert_device(
    device_uid: str,
    device_secret: str,
    user_id: Optional[int],
    name: Optional[str],
    firmware_ver: Optional[str] = None,
) -> int:
    """插入设备，返回主键。"""
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO device (device_uid, device_secret, user_id, name, status, firmware_ver)
            VALUES (%s, %s, %s, %s, 1, %s)
            """,
            (device_uid, device_secret, user_id, name, firmware_ver),
        )
        return int(cur.lastrowid)


def bind_to_user(device_id: int, user_id: int, name: Optional[str] = None) -> None:
    """将设备绑定到用户。"""
    with get_cursor(commit=True) as cur:
        if name:
            cur.execute(
                "UPDATE device SET user_id = %s, name = %s WHERE id = %s",
                (user_id, name, device_id),
            )
        else:
            cur.execute(
                "UPDATE device SET user_id = %s WHERE id = %s",
                (user_id, device_id),
            )


def update_device_name(device_id: int, name: str) -> None:
    """更新设备名称。"""
    with get_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE device SET name = %s WHERE id = %s",
            (name, device_id),
        )


def delete_device(device_id: int) -> None:
    """物理删除（外键级联子表）。"""
    with get_cursor(commit=True) as cur:
        cur.execute("DELETE FROM device WHERE id = %s", (device_id,))


def count_by_user(user_id: int) -> int:
    """用户设备数量。"""
    with get_cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS c FROM device WHERE user_id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        return int(row["c"]) if row else 0


def count_today_data_by_user(user_id: int) -> int:
    """用户名下设备今日上传数据条数。"""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) AS c
            FROM device_data dd
            INNER JOIN device d ON dd.device_id = d.id
            WHERE d.user_id = %s AND DATE(dd.recorded_at) = CURDATE()
            """,
            (user_id,),
        )
        row = cur.fetchone()
        return int(row["c"]) if row else 0
