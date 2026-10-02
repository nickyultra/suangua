# -*- coding: utf-8 -*-
"""HTTP 请求 / 响应模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from ..pipeline import MODES

_DATETIME_FORMATS = ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S")


class DivineRequest(BaseModel):
    question: str = ""
    mode: str = "liuyao"
    matter: str = "auto"  # auto = 由模型判定，否则取枚举值
    gender: str = ""
    numbers: list[int] | None = None
    at: str = ""                       # 起卦时间，留空取服务器当前时间
    throws: list[int] | None = None    # 六爻掷数，仅用于复现同一卦

    @field_validator("mode")
    @classmethod
    def _check_mode(cls, v: str) -> str:
        if v not in MODES:
            raise ValueError(f"未知起卦方式: {v}")
        return v

    def parsed_moment(self) -> datetime | None:
        if not self.at:
            return None
        for fmt in _DATETIME_FORMATS:
            try:
                return datetime.strptime(self.at, fmt)
            except ValueError:
                continue
        raise ValueError(f"无法解析时间: {self.at}")

    def parsed_numbers(self) -> tuple[int, int] | None:
        if self.numbers is None:
            return None
        if len(self.numbers) != 2:
            raise ValueError("报数需要两个整数")
        return int(self.numbers[0]), int(self.numbers[1])


class MetaResponse(BaseModel):
    modes: list[dict[str, str]]
    matters: list[dict[str, str]]
    llm_ready: bool
    model: str
    sect: int


class DivineResponse(BaseModel):
    result: dict
    matter: str
    gender: str
    matter_auto: bool
    llm_ready: bool
    notices: list[str] = Field(default_factory=list)
