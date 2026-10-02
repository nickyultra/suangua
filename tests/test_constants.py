# -*- coding: utf-8 -*-
"""静态表完备性与纳甲顺逆校验。"""

from __future__ import annotations

import pytest

from app.core import constants as C
from app.core.cast import build_gua
from app.core.paipan import set_najia

# 八卦纳甲全表：卦 -> (初, 二, 三, 四, 五, 上)
KNOWN_NAJIA = {
    "乾": ["甲子", "甲寅", "甲辰", "壬午", "壬申", "壬戌"],
    "坎": ["戊寅", "戊辰", "戊午", "戊申", "戊戌", "戊子"],
    "艮": ["丙辰", "丙午", "丙申", "丙戌", "丙子", "丙寅"],
    "震": ["庚子", "庚寅", "庚辰", "庚午", "庚申", "庚戌"],
    "巽": ["辛丑", "辛亥", "辛酉", "辛未", "辛巳", "辛卯"],
    "离": ["己卯", "己丑", "己亥", "己酉", "己未", "己巳"],
    "坤": ["乙未", "乙巳", "乙卯", "癸丑", "癸亥", "癸酉"],
    "兑": ["丁巳", "丁卯", "丁丑", "丁亥", "丁酉", "丁未"],
}


def test_hexagram_table_is_complete_and_consistent():
    assert len(C.HEXAGRAM_BY_TRIGRAM) == 64
    assert len(C.HEXAGRAM_ORDER) == 64
    assert set(C.HEXAGRAM_BY_TRIGRAM.values()) == set(C.HEXAGRAM_ORDER)
    # 每个上下卦组合恰有一卦
    assert len(set(C.HEXAGRAM_BY_TRIGRAM)) == 64


def test_eight_palaces_cover_all_hexagrams():
    assert len(C.GUA_GONG) == 64
    assert set(C.GUA_GONG) == set(C.HEXAGRAM_ORDER)
    for gong, (wuxing, members) in C._GONG_MEMBERS.items():
        assert len(members) == 8
        assert C.GONG_WUXING[gong] == wuxing


@pytest.mark.parametrize("tri", list(KNOWN_NAJIA))
def test_najia_matches_known_table(tri):
    """八卦纳甲：阳卦纳阳支顺行，阴卦纳阴支逆行。"""
    gua = build_gua(list(C.BAGUA_YAO[tri]) + list(C.BAGUA_YAO[tri]))
    set_najia(gua)
    assert [ln.ganzhi for ln in gua.lines] == KNOWN_NAJIA[tri]


def test_najia_yinyang_consistency():
    """阳卦六爻全纳阳支，阴卦全纳阴支。"""
    for tri in C.BAGUA:
        gua = build_gua(list(C.BAGUA_YAO[tri]) + list(C.BAGUA_YAO[tri]))
        set_najia(gua)
        zhis = {ln.zhi for ln in gua.lines}
        if tri in C.YANG_GUA:
            assert zhis <= C.ZHI_YANG
        else:
            assert not (zhis & C.ZHI_YANG)


def test_shi_ying_positions():
    """八纯卦世上应三；游魂世四应初；归魂世三应六。"""
    assert (C.SHI_POS["乾为天"], C.YING_POS["乾为天"]) == (6, 3)
    assert (C.SHI_POS["火地晋"], C.YING_POS["火地晋"]) == (4, 1)  # 游魂
    assert (C.SHI_POS["火天大有"], C.YING_POS["火天大有"]) == (3, 6)  # 归魂
    # 世应恒隔两位
    for name in C.HEXAGRAM_ORDER:
        shi, ying = C.SHI_POS[name], C.YING_POS[name]
        assert ((shi - 1 + 3) % 6) + 1 == ying


def test_liushen_rotation():
    """六神按日干起，六位一轮不重不漏。"""
    from app.core.paipan import set_liushen

    gua = build_gua([1] * 6)
    set_liushen(gua, "甲")
    assert [ln.liushen for ln in gua.lines] == list(C.LIUSHEN)
    set_liushen(gua, "戊")
    assert gua.lines[0].liushen == "勾陈"
    assert gua.lines[5].liushen == "朱雀"


@pytest.mark.parametrize(
    "day_gan,hour_zhi,expect",
    [("甲", "子", "甲"), ("己", "子", "甲"), ("戊", "子", "壬"),
     ("癸", "子", "壬"), ("乙", "子", "丙"), ("庚", "子", "丙"),
     ("戊", "未", "己"), ("丙", "午", "甲")],
)
def test_hour_gan_wushudun(day_gan, hour_zhi, expect):
    assert C.hour_gan(day_gan, hour_zhi) == expect


def test_wuxing_relation():
    assert C.wuxing_relation("金", "土") == "生我"
    assert C.wuxing_relation("金", "水") == "我生"
    assert C.wuxing_relation("金", "火") == "克我"
    assert C.wuxing_relation("金", "木") == "我克"
    assert C.wuxing_relation("金", "金") == "同我"
