# -*- coding: utf-8 -*-
"""占卜主流水线 N2–N6：取时、历法、起卦、排盘、定用神。

本模块完全确定：不联网、不调用模型，给定输入必得同一结果。
N1（问题理解）与 N7（解读）在 app.llm 中，由路由层编排。
"""

from __future__ import annotations

from datetime import datetime

from .core.calendar import DAY_BOUNDARY_SECT, compute_calendar
from .core.cast import cast_liuyao, cast_meihua_number, cast_meihua_time, liuyao_from_throws
from .core.models import DivinationResult
from .core.paipan import meihua_summary, paipan_liuyao
from .core.yongshen import locate_yongshen, select_yongshen

MODE_LIUYAO = "liuyao"
MODE_MEIHUA_NUMBER = "meihua_number"
MODE_MEIHUA_TIME = "meihua_time"

MODES = (MODE_LIUYAO, MODE_MEIHUA_NUMBER, MODE_MEIHUA_TIME)

MODE_LABELS = {
    MODE_LIUYAO: "六爻（金钱卦）",
    MODE_MEIHUA_NUMBER: "梅花易数·报数起卦",
    MODE_MEIHUA_TIME: "梅花易数·时间起卦",
}


def build_result(
    *,
    question: str,
    mode: str,
    matter: str = "self",
    gender: str = "",
    moment: datetime | None = None,
    numbers: tuple[int, int] | None = None,
    throws: list[int] | None = None,
    sect: int = DAY_BOUNDARY_SECT,
) -> DivinationResult:
    """跑完 N2–N6，返回结构化占卜结果。

    传入 throws 可用既定的六次掷数复现同一卦（网页先摇卦、再请求解读时用）。
    """
    if mode not in MODES:
        raise ValueError(f"未知起卦方式: {mode}")
    moment = moment or datetime.now()

    raw: dict = {}
    if mode == MODE_LIUYAO:
        cast = liuyao_from_throws(throws) if throws else cast_liuyao()
        ben, bian, hu = cast["ben"], cast["bian"], None
        ti = yong = ""
    elif mode == MODE_MEIHUA_NUMBER:
        if not numbers:
            raise ValueError("梅花报数起卦需要两个 1–99 的数")
        cast = cast_meihua_number(int(numbers[0]), int(numbers[1]))
        ben, bian, hu = cast["ben"], cast["bian"], cast["hu"]
        ti, yong = cast["ti"], cast["yong"]
    else:
        cast = cast_meihua_time(moment)
        ben, bian, hu = cast["ben"], cast["bian"], cast["hu"]
        ti, yong = cast["ti"], cast["yong"]

    raw = cast["raw"]
    cal = compute_calendar(moment, sect=sect)

    result = DivinationResult(
        mode=mode,
        question=question,
        matter=matter,
        gender=gender,
        calendar=cal,
        ben=ben,
        bian=bian,
        hu=hu,
        dong_yao=cast["dong_yao"],
        ti=ti,
        yong=yong,
        raw=raw,
    )

    if mode == MODE_LIUYAO:
        paipan_liuyao(ben, bian, cal)
        result.yongshen = select_yongshen(matter, gender)
        result.yongshen_pos = locate_yongshen(ben, result.yongshen)
    else:
        detail = meihua_summary(ti, yong)
        result.ti_yong_relation = detail["relation"]
        result.tiyong_detail = detail

    return result
