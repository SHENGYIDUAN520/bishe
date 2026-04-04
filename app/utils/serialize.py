# -*- coding: utf-8 -*-
"""
将数据库行中的 Decimal、datetime 等转为 JSON 友好类型。
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


def json_safe_value(v: Any) -> Any:
    """单值转换。"""
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat(sep=" ") if isinstance(v, datetime) else v.isoformat()
    return v


def json_safe_row(row: Optional[Dict]) -> Optional[Dict]:
    """字典行转换。"""
    if row is None:
        return None
    return {k: json_safe_value(v) for k, v in row.items()}


def json_safe_rows(rows: List[Dict]) -> List[Dict]:
    """多行转换。"""
    return [json_safe_row(r) or {} for r in rows]
