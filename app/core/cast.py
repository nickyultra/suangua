# -*- coding: utf-8 -*-
"""N4 起卦：六爻摇钱、梅花报数、梅花时间。

卦名一律查表得出，绝不交给模型生成。
"""

from __future__ import annotations

import random
from datetime import datetime

from .calendar import hour_zhi_number, lunar_month_day, year_zhi_number
from .constants import BAGUA_YAO, HEXAGRAM_BY_TRIGRAM, NUM_TO_BAGUA, YAO_TO_BAGUA
from .models import Gua, Line

# 摇钱结果 → (是否阳爻, 是否动爻)
#   6 老阴（动，变阳）  7 少阳（静）  8 少阴（静）  9 老阳（动，变阴）
TOSS_TABLE = {
    6: (False, True),
    7: (True, False),
    8: (False, False),
    9: (True, True),
}

_rng = random.SystemRandom()


def _trigrams(yao: list[bool]) -> tuple[str, str]:
    """六爻（初→上）→ (上卦, 下卦)。"""
    lower = YAO_TO_BAGUA[tuple(1 if y else 0 for y in yao[0:3])]
    upper = YAO_TO_BAGUA[tuple(1 if y else 0 for y in yao[3:6])]
    return upper, lower


def build_gua(yao: list[bool], moving: list[bool] | None = None) -> Gua:
    """由六爻阴阳构造卦体。yao 自初爻排到上爻。"""
    moving = moving or [False] * 6
    upper, lower = _trigrams(yao)
    name = HEXAGRAM_BY_TRIGRAM[(upper, lower)]
    lines = [
        Line(pos=i + 1, yang=yao[i], moving=moving[i]) for i in range(6)
    ]
    return Gua(name=name, upper=upper, lower=lower, lines=lines)


# ── 六爻（金钱卦）──────────────────────────────────────────────────────


def toss_once(rng: random.Random | None = None) -> tuple[int, list[int]]:
    """掷三枚铜钱，字面 3、背面 2。返回 (三数之和, 三枚正反)。"""
    r = rng or _rng
    coins = [r.choice((2, 3)) for _ in range(3)]
    return sum(coins), coins


def cast_liuyao(rng: random.Random | None = None) -> dict:
    """摇六次铜钱得本卦。返回本卦、变卦、动爻与原始掷数。"""
    throws: list[int] = []
    coins: list[list[int]] = []
    for _ in range(6):
        total, face = toss_once(rng)
        throws.append(total)
        coins.append(face)

    yao = [TOSS_TABLE[t][0] for t in throws]
    moving = [TOSS_TABLE[t][1] for t in throws]
    ben = build_gua(yao, moving)

    # 动爻阴阳互换得变卦
    bian = None
    if any(moving):
        bian_yao = [not y if m else y for y, m in zip(yao, moving)]
        bian = build_gua(bian_yao, [False] * 6)

    return {
        "ben": ben,
        "bian": bian,
        "dong_yao": [i + 1 for i, m in enumerate(moving) if m],
        "raw": {"throws": throws, "coins": coins},
    }


def liuyao_from_throws(throws: list[int]) -> dict:
    """由给定的六次掷数（自初爻到上爻）复原成卦，便于复现与测试。"""
    if len(throws) != 6 or any(t not in TOSS_TABLE for t in throws):
        raise ValueError("掷数须为 6 个，且取值在 6–9 之间")
    yao = [TOSS_TABLE[t][0] for t in throws]
    moving = [TOSS_TABLE[t][1] for t in throws]
    ben = build_gua(yao, moving)
    bian = None
    if any(moving):
        bian = build_gua(
            [not y if m else y for y, m in zip(yao, moving)], [False] * 6
        )
    return {
        "ben": ben,
        "bian": bian,
        "dong_yao": [i + 1 for i, m in enumerate(moving) if m],
        "raw": {"throws": throws},
    }


# ── 梅花易数 ──────────────────────────────────────────────────────────


def _num_to_bagua(n: int, mod: int) -> int:
    """取余，余 0 取 mod。"""
    r = n % mod
    return r if r else mod


def _meihua_from_upper_lower_dong(upper_num: int, lower_num: int, dong: int, raw: dict) -> dict:
    upper = NUM_TO_BAGUA[upper_num]
    lower = NUM_TO_BAGUA[lower_num]

    # 六爻自初至上 = 下卦三爻 + 上卦三爻
    yao = list(BAGUA_YAO[lower]) + list(BAGUA_YAO[upper])

    moving = [i + 1 == dong for i in range(6)]
    ben = build_gua(yao, moving)

    # 互卦：二三四为下互（作互卦下卦），三四五为上互（作互卦上卦）
    hu_lower_yao = [yao[1], yao[2], yao[3]]  # 二三四
    hu_upper_yao = [yao[2], yao[3], yao[4]]  # 三四五
    hu = build_gua(hu_lower_yao + hu_upper_yao, [False] * 6)

    # 变卦：动爻阴阳互换
    bian = build_gua(
        [not y if i + 1 == dong else y for i, y in enumerate(yao)], [False] * 6
    )

    # 体用：无动爻之卦为体，有动爻之卦为用
    if dong <= 3:  # 动爻在下卦 → 下卦为用、上卦为体
        ti_side, yong_side = upper, lower
    else:
        ti_side, yong_side = lower, upper

    return {
        "ben": ben,
        "hu": hu,
        "bian": bian,
        "dong_yao": [dong],
        "ti": ti_side,
        "yong": yong_side,
        "raw": raw,
    }


def cast_meihua_number(num1: int, num2: int) -> dict:
    """梅花报数起卦。两数各取 1–99。"""
    for n in (num1, num2):
        if not 1 <= n <= 99:
            raise ValueError("报数须在 1–99 之间")
    upper_num = _num_to_bagua(num1, 8)
    lower_num = _num_to_bagua(num2, 8)
    dong = _num_to_bagua(num1 + num2, 6)
    return _meihua_from_upper_lower_dong(
        upper_num, lower_num, dong, {"numbers": [num1, num2]}
    )


def cast_meihua_time(moment: datetime) -> dict:
    """梅花时间起卦。年支数 + 农历月 + 农历日 + 时辰数。"""
    yz = year_zhi_number(moment)
    month, day = lunar_month_day(moment)
    hz = hour_zhi_number(moment)

    base = yz + month + day
    upper_num = _num_to_bagua(base, 8)
    lower_num = _num_to_bagua(base + hz, 8)
    dong = _num_to_bagua(base + hz, 6)
    return _meihua_from_upper_lower_dong(
        upper_num, lower_num, dong,
        {"year_zhi": yz, "lunar_month": month, "lunar_day": day, "hour_zhi": hz},
    )
