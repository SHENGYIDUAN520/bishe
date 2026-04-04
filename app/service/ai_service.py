# -*- coding: utf-8 -*-
"""
AI 分析业务：优先调用火山方舟 OpenAI 兼容接口；未配置或失败时回退为本地统计+模板。
"""
import json
from typing import Optional, Tuple

from flask import current_app

from app.dao import ai_report_dao, device_dao, device_data_dao
from app.service import ark_ai_client


def _resolve_target_device(user_id: int, device_id: Optional[int]) -> Tuple[bool, str, Optional[int]]:
    """确定要分析的设备主键。"""
    if device_id is None:
        lst = device_dao.list_by_user_id(user_id)
        if not lst:
            return False, "暂无绑定设备，请先在设备页绑定或生成模拟设备", None
        return True, "", int(lst[0]["id"])
    row = device_dao.find_by_id(device_id)
    if not row or int(row.get("user_id") or 0) != int(user_id):
        return False, "设备不存在或无权分析", None
    return True, "", int(device_id)


def _local_parts(
    target_id: int,
    n: int,
    avg_t,
    min_t,
    max_t,
    avg_h,
) -> Tuple[str, str, str]:
    """无方舟时的标题、摘要、正文。"""
    title = "环境数据运行趋势（本地模拟分析）"
    if n == 0:
        summary = "近 72 小时内无传感数据，无法计算统计量。"
        content = (
            "【说明】本报告由平台根据本地数据库自动生成。\n"
            "当前设备在统计时间范围内没有数据记录。\n"
            "设备上线并上传数据后，可再次生成分析；若已配置方舟密钥与接入点，将优先调用大模型解读。"
        )
        return title, summary, content

    summary = (
        f"近 72 小时共 {n} 条数据；温度均值约 {float(avg_t):.1f}℃，"
        f"区间 {float(min_t):.1f}～{float(max_t):.1f}℃。"
    )
    content = (
        f"【数据概况】\n"
        f"- 样本条数：{n}\n"
        f"- 温度（℃）：平均 {float(avg_t):.2f}，最低 {float(min_t):.2f}，最高 {float(max_t):.2f}\n"
        f"- 湿度（%RH）：平均 {float(avg_h) if avg_h is not None else 0:.2f}\n\n"
        f"【趋势与异常（规则化描述）】\n"
        f"温度若在 18～28℃ 可视为常见舒适区间；具体场景需结合业务判断。\n"
    )
    return title, summary, content


def run_local_demo_analysis(user_id: int, device_id: Optional[int] = None) -> Tuple[bool, str, Optional[int]]:
    """
    生成分析报告并入库。
    若配置了 AI_API_KEY + AI_MODEL，则调用方舟；否则仅本地；方舟失败时自动降级。
    """
    ok, msg, target_id = _resolve_target_device(user_id, device_id)
    if not ok:
        return False, msg, None

    stats = device_data_dao.stats_for_device_range(target_id, 72)
    n = int(stats["n"] or 0) if stats else 0
    avg_t = stats.get("avg_t") if stats else None
    min_t = stats.get("min_t") if stats else None
    max_t = stats.get("max_t") if stats else None
    avg_h = stats.get("avg_h") if stats else None
    avg_l = stats.get("avg_l") if stats else None

    payload = {
        "device_id": target_id,
        "hours": 72,
        "sample_count": n,
        "temperature_avg": float(avg_t) if avg_t is not None else None,
        "temperature_min": float(min_t) if min_t is not None else None,
        "temperature_max": float(max_t) if max_t is not None else None,
        "humidity_avg": float(avg_h) if avg_h is not None else None,
        "illuminance_avg": float(avg_l) if avg_l is not None else None,
    }
    stats_json = json.dumps(payload, ensure_ascii=False, indent=2)

    lt, ls, lc = _local_parts(target_id, n, avg_t, min_t, max_t, avg_h)

    cfg = current_app.config
    api_key = (cfg.get("AI_API_KEY") or "").strip()
    model = (cfg.get("AI_MODEL") or "").strip()
    base_url = (cfg.get("ARK_BASE_URL") or "").strip()

    if api_key and model:
        user_prompt = (
            "请根据以下物联网终端统计数据撰写中文分析报告（面向运维人员）。\n"
            "要求：分三段——①概况摘要 ②趋势与异常判断 ③运维建议；总字数适中，勿编造不存在的数值。\n\n"
            f"{stats_json}"
        )
        messages = [
            {
                "role": "system",
                "content": "你是物联网环境监控系统中的数据分析助手，输出简体中文，语气专业、克制。",
            },
            {"role": "user", "content": user_prompt},
        ]
        ark_ok, ark_text = ark_ai_client.chat_completion(
            base_url, api_key, model, messages
        )
        if ark_ok:
            title = "智能分析报告（火山方舟）"
            summary = ark_text[:300] + ("…" if len(ark_text) > 300 else "")
            content = ark_text
            report_type = "volcengine_ark"
            rid = ai_report_dao.insert_report(
                user_id=user_id,
                device_id=target_id,
                report_type=report_type,
                title=title,
                summary=summary,
                content=content,
                chart_meta={"source": "ark", "stats": payload},
            )
            return True, "分析完成（已调用火山方舟大模型）", rid

        # 方舟失败：本地内容 + 错误说明
        title = lt
        summary = ls + f"（方舟调用失败：{ark_text[:120]}）"
        content = lc + f"\n\n---\n【方舟接口说明】{ark_text}"
        report_type = "local_demo_fallback"
        rid = ai_report_dao.insert_report(
            user_id=user_id,
            device_id=target_id,
            report_type=report_type,
            title=title,
            summary=summary,
            content=content,
            chart_meta={"ark_error": ark_text[:500], "stats": payload},
        )
        return True, "分析已保存（方舟不可用，已使用本地备用内容）", rid

    # 未配置密钥：纯本地
    rid = ai_report_dao.insert_report(
        user_id=user_id,
        device_id=target_id,
        report_type="local_demo",
        title=lt,
        summary=ls,
        content=lc,
        chart_meta={"stats": payload},
    )
    return True, "分析完成（本地模拟；可在 .env 配置 AI_API_KEY 与 AI_MODEL 启用方舟）", rid
