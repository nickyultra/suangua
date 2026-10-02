# -*- coding: utf-8 -*-
"""OpenAI 兼容模型客户端：N1 事项归类、N7 流式解卦。"""

from __future__ import annotations

import json
from typing import Iterator

from openai import OpenAI

from ..config import Settings
from ..core.models import DivinationResult
from ..core.yongshen import VALID_MATTERS
from .prompts import CLASSIFY_SYSTEM, build_system_prompt, build_user_prompt


class LLMNotConfigured(RuntimeError):
    """未配置 API Key —— 此时只出排盘，不出解读。"""


def get_client(settings: Settings) -> OpenAI:
    if not settings.llm_ready:
        raise LLMNotConfigured("未配置 LLM_API_KEY")
    return OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout,
    )


def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    return text.strip()


def classify(question: str, settings: Settings) -> dict:
    """N1：把问题归到固定事项枚举，并抽取性别。失败时退回 self。"""
    client = get_client(settings)
    resp = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": CLASSIFY_SYSTEM},
            {"role": "user", "content": question},
        ],
        temperature=0,
        max_tokens=80,
    )
    raw = resp.choices[0].message.content or ""
    try:
        data = json.loads(_strip_fence(raw))
    except (json.JSONDecodeError, IndexError):
        return {"matter": "self", "gender": ""}

    matter = data.get("matter")
    gender = data.get("gender") or ""
    if matter not in VALID_MATTERS:
        matter = "self"
    if gender not in ("男", "女"):
        gender = ""
    return {"matter": matter, "gender": gender}


def interpret_stream(result: DivinationResult, settings: Settings) -> Iterator[str]:
    """N7：流式解卦。"""
    client = get_client(settings)
    stream = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": build_user_prompt(result)},
        ],
        temperature=settings.llm_temperature,
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content


def interpret(result: DivinationResult, settings: Settings) -> str:
    """N7 的非流式版本，供命令行使用。"""
    return "".join(interpret_stream(result, settings))
