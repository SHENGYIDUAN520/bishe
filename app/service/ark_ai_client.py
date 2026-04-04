# -*- coding: utf-8 -*-
"""
火山引擎「方舟」OpenAI 兼容 Chat Completions 调用封装。
文档参考：https://www.volcengine.com/docs/82379/1330626
model 参数须填控制台中的「推理接入点 ID」（非展示名）。
"""
import time
from typing import Any, Dict, List, Tuple

import requests


def chat_completion(
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, Any]],
    *,
    temperature: float = 0.35,
    max_tokens: int = 2048,
    timeout: int = 90,
    max_retries: int = 3,
) -> Tuple[bool, str]:
    """
    调用 POST {base_url}/chat/completions。
    :return: (成功标志, 正文或错误说明)
    """
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    last_err = ""
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, json=body, headers=headers, timeout=timeout)
            if resp.status_code >= 500 and attempt < max_retries - 1:
                time.sleep(1.0 + attempt)
                continue
            if resp.status_code != 200:
                last_err = f"HTTP {resp.status_code}: {(resp.text or '')[:800]}"
                if resp.status_code in (429, 503) and attempt < max_retries - 1:
                    time.sleep(2.0 + attempt)
                    continue
                return False, last_err
            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                return False, "响应中无 choices 字段"
            content = (choices[0].get("message") or {}).get("content") or ""
            content = str(content).strip()
            if not content:
                return False, "模型返回空内容"
            return True, content
        except requests.RequestException as ex:
            last_err = f"请求异常：{ex!s}"
            if attempt < max_retries - 1:
                time.sleep(1.0 + attempt)
                continue
            return False, last_err
    return False, last_err or "重试失败"
