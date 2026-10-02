# -*- coding: utf-8 -*-
"""确定性内核的数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Line:
    """一爻。pos: 1=初爻 … 6=上爻。yang: True 为阳爻。"""

    pos: int
    yang: bool
    moving: bool = False
    # 六爻排盘填充
    gan: str = ""
    zhi: str = ""
    wuxing: str = ""
    liuqin: str = ""
    liushen: str = ""
    is_shi: bool = False
    is_ying: bool = False
    kong: bool = False  # 旬空

    @property
    def pos_name(self) -> str:
        return ("初", "二", "三", "四", "五", "上")[self.pos - 1]

    @property
    def ganzhi(self) -> str:
        return f"{self.gan}{self.zhi}"

    @property
    def symbol(self) -> str:
        """阳爻实线、阴爻断线，动爻加标记。"""
        base = "▅▅▅▅▅" if self.yang else "▅▅ ▅▅"
        if self.moving:
            base += " ○" if self.yang else " ×"
        return base


@dataclass
class Gua:
    """一个六爻卦体。lines 自初爻排到上爻，共六条。"""

    name: str
    upper: str
    lower: str
    lines: list[Line]
    gong: str = ""
    gong_wuxing: str = ""
    shi_pos: int = 0
    ying_pos: int = 0

    @property
    def symbol(self) -> str:
        from .constants import BAGUA_SYMBOL

        return BAGUA_SYMBOL[self.upper] + BAGUA_SYMBOL[self.lower]

    @property
    def full_name(self) -> str:
        return f"{self.name}（{self.upper}上{self.lower}下）"

    @property
    def moving_positions(self) -> list[int]:
        return [ln.pos for ln in self.lines if ln.moving]


@dataclass
class CalendarInfo:
    """N3 历法换算结果。"""

    solar_text: str
    lunar_text: str
    year_gz: str
    month_gz: str
    day_gz: str
    hour_gz: str
    month_jian: str  # 月建（月柱地支）
    day_chen: str    # 日辰（日柱地支）
    xun: str
    xun_kong: str
    jieqi: str = ""
    sect: int = 2


@dataclass
class DivinationResult:
    """一次完整占卜的结构化结果（N1–N6 的产物，供前端渲染与 N7 解读）。"""

    mode: str                    # liuyao / meihua_number / meihua_time
    question: str
    matter: str
    gender: str
    calendar: CalendarInfo
    ben: Gua                     # 本卦
    bian: Gua | None = None      # 变卦
    hu: Gua | None = None        # 互卦（梅花）
    dong_yao: list[int] = field(default_factory=list)
    # 六爻专有
    yongshen: str = ""           # 用神六亲（或「世」「应」）
    yongshen_pos: list[int] = field(default_factory=list)
    # 梅花专有
    ti: str = ""                 # 体卦
    yong: str = ""               # 用卦
    ti_yong_relation: str = ""   # 体用生克断语
    tiyong_detail: dict[str, Any] = field(default_factory=dict)  # 体用五行、吉凶、应期
    raw: dict[str, Any] = field(default_factory=dict)  # 原始掷数 / 报数

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
