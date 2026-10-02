# -*- coding: utf-8 -*-
"""N3 历法换算：公历 → 农历、四柱干支、月建、日辰、旬空。

封装 lunar-python。干支一律取自该库，不自行推算，避免立春换年、节气换月、
早晚子时三处边界出错。
"""

from __future__ import annotations

from datetime import datetime

from lunar_python import Solar

from .constants import GAN, ZHI, hour_gan
from .models import CalendarInfo

# 晚子时（23:00–23:59）日柱归属流派：
#   2 = 日柱算当天（默认，与万年历同）
#   1 = 日柱算次日
DAY_BOUNDARY_SECT = 2


def hour_zhi(hour: int) -> str:
    """小时 → 时辰地支。子时跨日，23:00 起即入子。"""
    return ZHI[((hour + 1) // 2) % 12]


def compute_calendar(moment: datetime, sect: int = DAY_BOUNDARY_SECT) -> CalendarInfo:
    """把公历时刻换算成占卜所需的历法信息。"""
    solar = Solar.fromYmdHms(
        moment.year, moment.month, moment.day, moment.hour, moment.minute, moment.second
    )
    lunar = solar.getLunar()

    year_gz = lunar.getYearInGanZhiExact()    # 立春换年（精确到时刻）
    month_gz = lunar.getMonthInGanZhiExact()  # 节气换月

    if sect == 1:
        day_gz = lunar.getDayInGanZhiExact()
        xun, xun_kong = lunar.getDayXunExact(), lunar.getDayXunKongExact()
    else:
        day_gz = lunar.getDayInGanZhiExact2()
        xun, xun_kong = lunar.getDayXunExact2(), lunar.getDayXunKongExact2()

    # 时柱由所选日柱经五鼠遁推出，保证日、时同源自洽
    zhi = hour_zhi(moment.hour)
    hour_gz = hour_gan(day_gz[0], zhi) + zhi

    return CalendarInfo(
        solar_text=moment.strftime("%Y-%m-%d %H:%M"),
        lunar_text=lunar.toString(),
        year_gz=year_gz,
        month_gz=month_gz,
        day_gz=day_gz,
        hour_gz=hour_gz,
        month_jian=month_gz[1],
        day_chen=day_gz[1],
        xun=xun,
        xun_kong=xun_kong,
        jieqi=lunar.getJieQi(),
        sect=sect,
    )


def lunar_month_day(moment: datetime) -> tuple[int, int]:
    """农历月、日（闰月取月数本身，如闰二月返回 2），供梅花时间起卦用。"""
    lunar = Solar.fromYmdHms(
        moment.year, moment.month, moment.day, moment.hour, moment.minute, 0
    ).getLunar()
    return abs(lunar.getMonth()), lunar.getDay()


def year_zhi_number(moment: datetime) -> int:
    """年支序数：子 1 … 亥 12，供梅花时间起卦用。立春换年。"""
    year_gz = Solar.fromYmdHms(
        moment.year, moment.month, moment.day, moment.hour, moment.minute, 0
    ).getLunar().getYearInGanZhiExact()
    return ZHI.index(year_gz[1]) + 1


def hour_zhi_number(moment: datetime) -> int:
    """时辰序数：子 1 … 亥 12。"""
    return ZHI.index(hour_zhi(moment.hour)) + 1


def gz_parts(ganzhi: str) -> tuple[str, str]:
    return ganzhi[0], ganzhi[1]


__all__ = [
    "compute_calendar",
    "lunar_month_day",
    "year_zhi_number",
    "hour_zhi_number",
    "hour_zhi",
    "gz_parts",
    "GAN",
    "ZHI",
]
