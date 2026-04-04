# -*- coding: utf-8 -*-
"""
AI 分析报告表访问。
"""
from typing import Dict, List, Optional

from app.db import get_cursor


def list_by_user(user_id: int, limit: int = 50) -> List[Dict]:
    """用户报告列表。"""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, device_id, report_type, title, summary, created_at
            FROM ai_report
            WHERE user_id = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        return list(cur.fetchall())


def find_by_id_for_user(report_id: int, user_id: int) -> Optional[Dict]:
    """详情（校验归属）。"""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, device_id, report_type, title, summary, content, chart_meta, created_at, updated_at
            FROM ai_report
            WHERE id = %s AND user_id = %s
            LIMIT 1
            """,
            (report_id, user_id),
        )
        return cur.fetchone()


def insert_report(
    user_id: int,
    device_id: Optional[int],
    report_type: str,
    title: str,
    summary: str,
    content: str,
    chart_meta: Optional[Dict] = None,
) -> int:
    """新增报告。"""
    import json

    meta = json.dumps(chart_meta, ensure_ascii=False) if chart_meta else None
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO ai_report (user_id, device_id, report_type, title, summary, content, chart_meta)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, device_id, report_type, title, summary, content, meta),
        )
        return int(cur.lastrowid)
