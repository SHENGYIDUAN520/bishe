# -*- coding: utf-8 -*-
"""
设备级告警设置访问（每台设备独立阈值）。
"""
from typing import Dict, List, Optional

from app.db import get_cursor


def _ensure_table() -> None:
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS device_alert_setting (
              device_id BIGINT UNSIGNED NOT NULL,
              temp_warn_high DECIMAL(6,2) NULL,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              PRIMARY KEY (device_id),
              CONSTRAINT fk_das_device FOREIGN KEY (device_id) REFERENCES device (id)
                ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='设备告警设置';
            """
        )


def upsert_temp_warn_high(device_id: int, temp_warn_high: Optional[float]) -> None:
    _ensure_table()
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO device_alert_setting (device_id, temp_warn_high)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE temp_warn_high = VALUES(temp_warn_high)
            """,
            (device_id, temp_warn_high),
        )


def get_by_device(device_id: int) -> Optional[Dict]:
    _ensure_table()
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT device_id, temp_warn_high, updated_at
            FROM device_alert_setting
            WHERE device_id = %s
            LIMIT 1
            """,
            (device_id,),
        )
        return cur.fetchone()


def list_by_device_ids(device_ids: List[int]) -> Dict[int, Optional[float]]:
    _ensure_table()
    if not device_ids:
        return {}
    placeholders = ", ".join(["%s"] * len(device_ids))
    with get_cursor() as cur:
        cur.execute(
            f"""
            SELECT device_id, temp_warn_high
            FROM device_alert_setting
            WHERE device_id IN ({placeholders})
            """,
            tuple(device_ids),
        )
        rows = cur.fetchall() or []
        return {int(r["device_id"]): r.get("temp_warn_high") for r in rows}


def get_alert_contact_by_device(device_id: int) -> Optional[Dict]:
    """查询设备归属用户的告警联系人信息与设备阈值。"""
    _ensure_table()
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT u.id AS user_id, u.username, u.email, u.phone, d.device_uid, d.name AS device_name,
                   s.temp_warn_high
            FROM device d
            INNER JOIN `user` u ON d.user_id = u.id
            LEFT JOIN device_alert_setting s ON s.device_id = d.id
            WHERE d.id = %s
            LIMIT 1
            """,
            (device_id,),
        )
        return cur.fetchone()
