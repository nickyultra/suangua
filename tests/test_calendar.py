# -*- coding: utf-8 -*-
"""历法对拍测试。

预期值不取自 lunar-python 自身：日时柱与独立实现 cnlunar 逐日对拍，
年月柱另按节气/立春的精确时刻写死断言。

注意两库口径差异（已核实，非缺陷）：
  - cnlunar 的月柱以「节气当天」换月，本实现以节气「精确时刻」换月；
  - cnlunar 的年柱以「春节」换年，本实现以「立春」换年（六爻/八字通行）。
故年月柱仅在两者口径必然一致的区间对拍。
"""

from __future__ import annotations

import datetime

import cnlunar
import pytest
from lunar_python import Solar

from app.core.calendar import (
    compute_calendar,
    hour_zhi,
    hour_zhi_number,
    lunar_month_day,
    year_zhi_number,
)

D = datetime.datetime

# 2026 全年逐日；取 12:00 属午时，避开早/晚子时的流派分歧
_DAYS = [D(2026, 1, 1) + datetime.timedelta(days=i) for i in range(365)]

# 2026 年关键节气精确时刻（lunar-python 节气表）
_LICHUN = D(2026, 2, 4, 4, 2, 8)
_CHUNJIE = D(2026, 2, 17)  # 农历正月初一


def _is_jieqi_day(day: datetime.datetime) -> bool:
    return bool(Solar.fromYmdHms(day.year, day.month, day.day, 12, 0, 0).getLunar().getJieQi())


def _cnlunar(moment: datetime.datetime):
    return cnlunar.Lunar(moment, godType="8char")


# ── 逐日对拍 ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("day", _DAYS, ids=lambda d: d.strftime("%m-%d"))
def test_day_and_hour_pillar_match_cnlunar(day):
    """日柱、时柱与独立实现逐日一致（全年 365 天）。"""
    moment = day.replace(hour=12)
    ours = compute_calendar(moment)
    theirs = _cnlunar(moment)
    assert ours.day_gz == theirs.day8Char
    assert ours.hour_gz == theirs.twohour8Char


@pytest.mark.parametrize("day", _DAYS, ids=lambda d: d.strftime("%m-%d"))
def test_year_and_month_pillar_match_cnlunar(day):
    """年、月柱在口径一致处对拍：剔除节气当日与立春至春节之间的窗口。"""
    if _is_jieqi_day(day):
        pytest.skip("节气当日两库换柱口径不同")
    if _LICHUN <= day < _CHUNJIE:
        pytest.skip("立春至春节间两库换年口径不同")
    moment = day.replace(hour=12)
    ours = compute_calendar(moment)
    theirs = _cnlunar(moment)
    assert ours.year_gz == theirs.year8Char
    assert ours.month_gz == theirs.month8Char


# ── 精确时刻边界 ─────────────────────────────────────────────────────


def test_lichun_switches_year_at_exact_moment():
    """立春 2026-02-04 04:02:08：年柱在该时刻换，非当日零点、非春节。"""
    assert compute_calendar(D(2026, 2, 4, 2, 0)).year_gz == "乙巳"
    assert compute_calendar(D(2026, 2, 4, 5, 0)).year_gz == "丙午"
    # 立春前一日整体仍属乙巳
    assert compute_calendar(D(2026, 2, 3, 23, 0)).year_gz == "乙巳"


def test_jieqi_switches_month_at_exact_moment():
    """月柱按节气精确时刻切换，非节气当日的零点。"""
    # 小寒 2026-01-05 16:23:10：由子月入丑月
    assert compute_calendar(D(2026, 1, 5, 12, 0)).month_jian == "子"
    assert compute_calendar(D(2026, 1, 5, 23, 0)).month_jian == "丑"
    # 惊蛰 2026-03-05 21:59:00：由寅月入卯月
    assert compute_calendar(D(2026, 3, 5, 12, 0)).month_jian == "寅"
    assert compute_calendar(D(2026, 3, 5, 23, 30)).month_jian == "卯"


def test_hour_zhi_spans_days():
    """子时跨日：23 时与 0 时同属子。"""
    assert hour_zhi(23) == "子"
    assert hour_zhi(0) == "子"
    assert hour_zhi(1) == "丑"
    assert hour_zhi(12) == "午"
    assert hour_zhi_number(D(2026, 10, 1, 0, 30)) == 1
    assert hour_zhi_number(D(2026, 10, 1, 23, 30)) == 1


def test_late_zi_hour_sect():
    """晚子时日柱流派：sect2 算当天，sect1 算次日；时柱与所选日柱自洽。"""
    moment = D(2026, 10, 1, 23, 30)
    assert compute_calendar(moment, sect=2).day_gz == "戊申"
    assert compute_calendar(moment, sect=1).day_gz == "己酉"
    assert compute_calendar(moment, sect=2).hour_gz == "壬子"  # 戊日五鼠遁
    assert compute_calendar(moment, sect=1).hour_gz == "甲子"  # 己日五鼠遁


def test_xunkong():
    """旬空由日柱推：戊申属甲辰旬，空寅卯。"""
    cal = compute_calendar(D(2026, 10, 1, 14, 30))
    assert cal.day_gz == "戊申"
    assert cal.xun == "甲辰"
    assert cal.xun_kong == "寅卯"


def test_meihua_inputs():
    """梅花时间起卦所需的年支数、农历月日、时辰数。"""
    moment = D(2026, 10, 1, 14, 30)
    assert year_zhi_number(moment) == 7  # 丙午年，午为第七支
    assert lunar_month_day(moment) == (8, 21)
    assert hour_zhi_number(moment) == 8  # 未时
