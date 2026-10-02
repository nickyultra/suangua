# -*- coding: utf-8 -*-
"""起卦测试：六爻掷数 → 本卦/动爻/变卦；梅花 → 本卦/互卦/变卦/体用。"""

from __future__ import annotations

import random
from datetime import datetime

import pytest

from app.core.cast import (
    cast_liuyao,
    cast_meihua_number,
    cast_meihua_time,
    liuyao_from_throws,
)

# (掷数自初爻到上爻, 本卦, 动爻, 变卦)
LIUYAO_CASES = [
    ([7, 7, 7, 7, 7, 7], "乾为天", [], None),
    ([8, 8, 8, 8, 8, 8], "坤为地", [], None),
    ([9, 7, 7, 7, 7, 7], "乾为天", [1], "天风姤"),   # 老阳动，初爻变阴
    ([6, 8, 8, 8, 8, 8], "坤为地", [1], "地雷复"),   # 老阴动，初爻变阳
    ([6, 6, 6, 6, 6, 6], "坤为地", [1, 2, 3, 4, 5, 6], "乾为天"),
    ([9, 9, 9, 9, 9, 9], "乾为天", [1, 2, 3, 4, 5, 6], "坤为地"),
]


@pytest.mark.parametrize("throws,ben,dong,bian", LIUYAO_CASES)
def test_liuyao_from_throws(throws, ben, dong, bian):
    r = liuyao_from_throws(throws)
    assert r["ben"].name == ben
    assert r["dong_yao"] == dong
    assert (r["bian"].name if r["bian"] else None) == bian


def test_liuyao_moving_flag_follows_6_and_9():
    r = liuyao_from_throws([6, 7, 8, 9, 7, 8])
    assert [ln.moving for ln in r["ben"].lines] == [True, False, False, True, False, False]
    assert [ln.yang for ln in r["ben"].lines] == [False, True, False, True, True, False]


def test_liuyao_throws_are_seeded_reproducibly():
    """给定随机源，掷数可复现。"""
    a = cast_liuyao(random.Random(42))
    b = cast_liuyao(random.Random(42))
    assert a["raw"]["throws"] == b["raw"]["throws"]
    assert a["ben"].name == b["ben"].name


def test_liuyao_coin_faces_sum_to_throw():
    r = cast_liuyao(random.Random(7))
    for total, coins in zip(r["raw"]["throws"], r["raw"]["coins"]):
        assert sum(coins) == total
        assert all(c in (2, 3) for c in coins)
        assert total in (6, 7, 8, 9)


@pytest.mark.parametrize("bad", [[7, 7, 7], [7, 7, 7, 7, 7, 10], [5, 7, 7, 7, 7, 7]])
def test_liuyao_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        liuyao_from_throws(bad)


def test_meihua_number_golden():
    """报数 7、7：上艮下艮为艮为山，互雷水解，变山风蛊，动爻二。"""
    r = cast_meihua_number(7, 7)
    assert r["ben"].name == "艮为山"
    assert r["hu"].name == "雷水解"
    assert r["bian"].name == "山风蛊"
    assert r["dong_yao"] == [2]
    # 动爻在下卦 → 上卦为体、下卦为用
    assert (r["ti"], r["yong"]) == ("艮", "艮")


def test_meihua_number_modulo_wraps_to_eight_and_six():
    """余 0 取 8 / 6。"""
    r = cast_meihua_number(8, 8)   # 8%8=0→8 坤；和16%6=4
    assert r["ben"].upper == "坤" and r["ben"].lower == "坤"
    assert r["dong_yao"] == [4]
    r2 = cast_meihua_number(3, 3)  # 3%8=3 离；和6%6=0→6
    assert r2["ben"].upper == "离" and r2["ben"].lower == "离"
    assert r2["dong_yao"] == [6]


@pytest.mark.parametrize("a,b", [(0, 5), (5, 100), (-1, 5)])
def test_meihua_number_rejects_out_of_range(a, b):
    with pytest.raises(ValueError):
        cast_meihua_number(a, b)


def test_meihua_time_golden():
    """2026-10-01 14:30：年支7+农历8月+21日=36 → 上震下震为震为雷，动爻二。"""
    r = cast_meihua_time(datetime(2026, 10, 1, 14, 30))
    assert r["raw"] == {"year_zhi": 7, "lunar_month": 8, "lunar_day": 21, "hour_zhi": 8}
    assert r["ben"].name == "震为雷"
    assert r["hu"].name == "水山蹇"
    assert r["bian"].name == "雷泽归妹"
    assert r["dong_yao"] == [2]
    assert (r["ti"], r["yong"]) == ("震", "震")


def test_meihua_tiyong_side_by_moving_trigram():
    """动爻在上卦 → 下卦为体；动爻在下卦 → 上卦为体。"""
    lower_moving = cast_meihua_number(3, 3)  # 动爻 6，在上卦
    assert lower_moving["dong_yao"] == [6]
    assert lower_moving["ti"] == lower_moving["ben"].lower
    assert lower_moving["yong"] == lower_moving["ben"].upper
