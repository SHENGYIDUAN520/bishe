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
    environment_type: str,
    custom_context: Optional[str],
) -> Tuple[str, str, str]:
    """无方舟时的标题、摘要、正文。"""
    # 根据场景调整标题与建议文字（本地模板不依赖大模型）
    if environment_type == "machine_room":
        title = "机房环境数据运行趋势（本地模拟分析）"
    elif environment_type == "factory":
        title = "工厂环境数据运行趋势（本地模拟分析）"
    elif environment_type == "custom":
        title = "自定义场景环境数据运行趋势（本地模拟分析）"
    else:
        title = "家庭环境数据运行趋势（本地模拟分析）"

    scenario_line = ""
    if environment_type == "machine_room":
        scenario_line = "本报告面向机房运维，重点关注温湿度对设备稳定与散热的影响。"
    elif environment_type == "factory":
        scenario_line = "本报告面向工厂运维，重点关注温湿度对工艺稳定与安全风险的影响。"
    elif environment_type == "custom":
        scenario_line = f"本报告面向自定义场景：{custom_context or '（未提供具体描述）'}"
    else:
        scenario_line = "本报告面向家庭使用场景，重点关注温湿度舒适性与日常安全隐患。"

    if n == 0:
        summary = f"近 72 小时内无传感数据，无法计算统计量。{scenario_line}"
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

    overview = (
        f"【数据概况】\n"
        f"- 样本条数：{n}\n"
        f"- 温度（℃）：平均 {float(avg_t):.2f}，最低 {float(min_t):.2f}，最高 {float(max_t):.2f}\n"
        f"- 湿度（%RH）：平均 {float(avg_h) if avg_h is not None else 0:.2f}\n\n"
    )
    env_rules = ""
    if environment_type == "machine_room":
        env_rules = (
            "【趋势与异常（机房化描述）】\n"
            "- 建议温度保持在设备允许范围内，避免长期高温影响稳定运行。\n"
            "- 若发现湿度异常，需结合机柜散热与除湿设备状态检查。\n"
            "【运维建议】\n"
            "- 定期巡检空调/除湿/风道，记录关键运行参数。\n"
            "- 对异常波动进行联动告警阈值配置（后续可在平台扩展）。\n"
        )
    elif environment_type == "factory":
        env_rules = (
            "【趋势与异常（工厂化描述）】\n"
            "- 温湿度波动可能影响工艺稳定性与产品一致性。\n"
            "- 若出现明显偏离，应排查车间空调/加湿/排风系统与门窗开闭工况。\n"
            "【运维建议】\n"
            "- 将环境数据纳入工艺过程管理，必要时设定更严格的阈值。\n"
            "- 对异常时段与产线运行数据做关联分析。\n"
        )
    elif environment_type == "custom":
        env_rules = (
            "【趋势与异常（自定义场景描述）】\n"
            f"- {scenario_line}\n"
            "【运维建议】\n"
            "- 根据自定义场景要求，进一步细化告警阈值与处置流程。\n"
        )
    else:
        env_rules = (
            "【趋势与异常（家庭化描述）】\n"
            "- 温度若在 18～28℃ 可视为常见舒适区间；具体仍需结合个人作息与体感。\n"
            "【运维建议】\n"
            "- 建议根据体感与湿度适度开窗通风或使用除湿/加湿设备。\n"
            "- 若长期偏高湿度，注意霉变风险与用电安全。\n"
        )

    content = overview + env_rules
    return title, summary, content


def run_local_demo_analysis(
    user_id: int,
    device_id: Optional[int] = None,
    environment_type: str = "home",
    custom_context: Optional[str] = None,
) -> Tuple[bool, str, Optional[int]]:
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
        "environment_type": environment_type,
        "custom_context": custom_context,
    }
    stats_json = json.dumps(payload, ensure_ascii=False, indent=2)

    lt, ls, lc = _local_parts(
        target_id, n, avg_t, min_t, max_t, avg_h, environment_type, custom_context
    )

    cfg = current_app.config
    api_key = (cfg.get("AI_API_KEY") or "").strip()
    model = (cfg.get("AI_MODEL") or "").strip()
    base_url = (cfg.get("ARK_BASE_URL") or "").strip()
    ai_timeout = int(cfg.get("AI_HTTP_TIMEOUT") or 12)
    ai_retries = int(cfg.get("AI_MAX_RETRIES") or 2)

    if api_key and model:
        if environment_type == "machine_room":
            scenario_text = "场景：机房/机柜/服务器房。重点关注温湿度对设备散热、稳定运行与安全风险的影响。"
        elif environment_type == "factory":
            scenario_text = "场景：工厂/车间。重点关注温湿度对工艺稳定性、质量一致性与安全风险的影响。"
        elif environment_type == "custom":
            scenario_text = f"场景：自定义。用户要求：{custom_context or '（未提供具体描述）'}"
        else:
            scenario_text = "场景：普通家庭。重点关注温湿度舒适性、日常健康与用电安全风险。"
        user_prompt = (
            "请根据以下物联网终端统计数据撰写中文分析报告（面向运维/管理人员）。\n"
            "要求：分三段——①概况摘要 ②趋势与异常判断 ③运维建议；总字数适中，勿编造不存在的数值。\n\n"
            f"{scenario_text}\n\n{stats_json}"
        )
        messages = [
            {
                "role": "system",
                "content": "你是物联网环境监控系统中的数据分析助手，输出简体中文，语气专业、克制。不要编造数据；只使用提供的统计数据做推断。",
            },
            {"role": "user", "content": user_prompt},
        ]
        ark_ok, ark_text = ark_ai_client.chat_completion(
            base_url,
            api_key,
            model,
            messages,
            timeout=ai_timeout,
            max_retries=ai_retries,
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


def generate_temp_alert_advice(temp: float, humidity: Optional[float], threshold: float) -> str:
    """温度告警建议：优先方舟，失败则本地规则。"""
    local = (
        f"当前温度 {temp:.1f}℃ 已超过阈值 {threshold:.1f}℃。"
        "建议先检查环境散热/通风；若持续超温，请降低设备负载并排查传感器与供电。"
    )
    cfg = current_app.config
    api_key = (cfg.get("AI_API_KEY") or "").strip()
    model = (cfg.get("AI_MODEL") or "").strip()
    base_url = (cfg.get("ARK_BASE_URL") or "").strip()
    ai_timeout = int(cfg.get("AI_HTTP_TIMEOUT") or 12)
    ai_retries = int(cfg.get("AI_MAX_RETRIES") or 2)
    if not api_key or not model:
        return local

    hum_txt = f"{float(humidity):.1f}%RH" if humidity is not None else "未知"
    messages = [
        {
            "role": "system",
            "content": "你是物联网运维告警助手。请给出 2-3 条简短、可执行、中文建议。",
        },
        {
            "role": "user",
            "content": (
                f"温度告警：当前温度 {temp:.1f}℃，阈值 {threshold:.1f}℃，湿度 {hum_txt}。"
                "请给出简洁处置建议（不要编造额外数据）。"
            ),
        },
    ]
    ok, text = ark_ai_client.chat_completion(
        base_url,
        api_key,
        model,
        messages,
        timeout=ai_timeout,
        max_retries=ai_retries,
    )
    return text.strip() if ok and text.strip() else local
