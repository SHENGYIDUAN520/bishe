# -*- coding: utf-8 -*-
"""
用户告警设置访问。
"""
from typing import Dict, Optional

from app.db import get_cursor


def _ensure_table() -> None:
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_alert_setting (
              user_id BIGINT UNSIGNED NOT NULL,
              temp_warn_high DECIMAL(6,2) NULL,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              PRIMARY KEY (user_id),
              CONSTRAINT fk_uas_user FOREIGN KEY (user_id) REFERENCES `user` (id)
                ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户告警设置';
            """
        )


def get_by_user(user_id: int) -> Optional[Dict]:
    _ensure_table()
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT user_id, temp_warn_high, updated_at
            FROM user_alert_setting
            WHERE user_id = %s
            LIMIT 1
            """,
            (user_id,),
        )
        return cur.fetchone()


def upsert_temp_warn_high(user_id: int, temp_warn_high: Optional[float]) -> None:
    _ensure_table()
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO user_alert_setting (user_id, temp_warn_high)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE temp_warn_high = VALUES(temp_warn_high)
            """,
            (user_id, temp_warn_high),
        )


def get_alert_contact_by_device(device_id: int) -> Optional[Dict]:
    """查询设备归属用户的告警联系人信息与阈值。"""
    _ensure_table()
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT u.id AS user_id, u.username, u.email, u.phone, d.device_uid, d.name AS device_name,
                   s.temp_warn_high
            FROM device d
            INNER JOIN `user` u ON d.user_id = u.id
            LEFT JOIN user_alert_setting s ON s.user_id = u.id
            WHERE d.id = %s
            LIMIT 1
            """,
            (device_id,),
        )
        return cur.fetchone()

