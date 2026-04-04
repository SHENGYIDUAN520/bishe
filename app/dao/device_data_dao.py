# -*- coding: utf-8 -*-
"""
设备传感数据表访问。
"""
from typing import Any, Dict, List, Optional, Tuple

from app.db import get_cursor


def latest_by_device(device_id: int) -> Optional[Dict]:
    """某设备最新一条数据。"""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, device_id, temperature, humidity, illuminance, recorded_at
            FROM device_data
            WHERE device_id = %s
            ORDER BY recorded_at DESC
            LIMIT 1
            """,
            (device_id,),
        )
        return cur.fetchone()


def history_by_device(
    device_id: int,
    start: Optional[str],
    end: Optional[str],
    page: int,
    page_size: int,
) -> Tuple[List[Dict], int]:
    """
    分页历史数据。
    :return: (列表, 总条数)
    """
    where = "device_id = %s"
    params: List[Any] = [device_id]
    if start:
        where += " AND recorded_at >= %s"
        params.append(start)
    if end:
        where += " AND recorded_at <= %s"
        params.append(end)

    with get_cursor() as cur:
        cur.execute(
            f"SELECT COUNT(*) AS c FROM device_data WHERE {where}",
            tuple(params),
        )
        total = int(cur.fetchone()["c"])
        offset = (page - 1) * page_size
        cur.execute(
            f"""
            SELECT id, device_id, temperature, humidity, illuminance, recorded_at
            FROM device_data
            WHERE {where}
            ORDER BY recorded_at DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params) + (page_size, offset),
        )
        return list(cur.fetchall()), total


def insert_row(
    device_id: int,
    temperature: Optional[float],
    humidity: Optional[float],
    illuminance: Optional[float],
    recorded_at: str,
) -> int:
    """插入一条数据。"""
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO device_data (device_id, temperature, humidity, illuminance, recorded_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (device_id, temperature, humidity, illuminance, recorded_at),
        )
        return int(cur.lastrowid)


def stats_for_device_range(device_id: int, hours: int = 24) -> Optional[Dict]:
    """最近若干小时简单统计（供模拟 AI 使用）。"""
    h = int(hours)
    if h < 1 or h > 24 * 14:
        h = 24
    # INTERVAL 占位在部分环境下不兼容，小时数经 int 校验后直接拼接
    with get_cursor() as cur:
        cur.execute(
            f"""
            SELECT
              COUNT(*) AS n,
              AVG(temperature) AS avg_t,
              MIN(temperature) AS min_t,
              MAX(temperature) AS max_t,
              AVG(humidity) AS avg_h,
              AVG(illuminance) AS avg_l
            FROM device_data
            WHERE device_id = %s
              AND recorded_at >= DATE_SUB(NOW(), INTERVAL {h} HOUR)
            """,
            (device_id,),
        )
        return cur.fetchone()
