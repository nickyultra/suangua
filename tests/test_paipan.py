# -*- coding: utf-8 -*-
"""排盘测试：纳甲、八宫、世应、六亲、六神、旬空的黄金样本。"""

from __future__ import annotations

import pytest

from app.core.cast import build_gua, liuyao_from_throws
from app.core.models import CalendarInfo
from app.core.paipan import evaluate_ti_yong, meihua_summary, paipan_liuyao


def _cal(day_gz="甲子", xun_kong="戌亥", xun="甲子") -> CalendarInfo:
    """构造一个只含排盘所需字段的历法信息。"""
    return CalendarInfo(
        solar_text="2026-01-01 00:00",
        lunar_text="",
        year_gz="乙巳",
        month_gz="戊子",
        day_gz=day_gz,
        hour_gz="甲子",
        month_jian="子",
        day_chen="子",
        xun=xun,
        xun_kong=xun_kong,
    )


def test_qian_weitian_full_chart():
    """乾为天 甲子日：经典装卦。"""
    r = liuyao_from_throws([7] * 6)
    ben = r["ben"]
    paipan_liuyao(ben, None, _cal(day_gz="甲子", xun_kong="戌亥"))

    assert (ben.gong, ben.gong_wuxing) == ("乾", "金")
    assert (ben.shi_pos, ben.ying_pos) == (6, 3)

    assert [ln.ganzhi for ln in ben.lines] == ["甲子", "甲寅", "甲辰", "壬午", "壬申", "壬戌"]
    assert [ln.liuqin for ln in ben.lines] == ["子孙", "妻财", "父母", "官鬼", "兄弟", "父母"]
    assert [ln.liushen for ln in ben.lines] == ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"]
    assert [ln.pos for ln in ben.lines if ln.is_shi] == [6]
    assert [ln.pos for ln in ben.lines if ln.is_ying] == [3]
    # 甲子旬空戌亥 → 仅上爻壬戌落空
    assert [ln.pos for ln in ben.lines if ln.kong] == [6]


def test_kun_weidi_full_chart():
    """坤为地：六亲以坤宫土为我。"""
    r = liuyao_from_throws([8] * 6)
    ben = r["ben"]
    paipan_liuyao(ben, None, _cal())

    assert (ben.gong, ben.gong_wuxing) == ("坤", "土")
    assert [ln.ganzhi for ln in ben.lines] == ["乙未", "乙巳", "乙卯", "癸丑", "癸亥", "癸酉"]
    assert [ln.liuqin for ln in ben.lines] == ["兄弟", "父母", "官鬼", "兄弟", "妻财", "子孙"]
    # 戌亥空 → 五爻癸亥落空
    assert [ln.pos for ln in ben.lines if ln.kong] == [5]


def test_liushen_shifts_with_day_gan():
    """六神起点随日干变。"""
    ben = liuyao_from_throws([7] * 6)["ben"]
    paipan_liuyao(ben, None, _cal(day_gz="戊申"))
    assert ben.lines[0].liushen == "勾陈"
    assert ben.lines[5].liushen == "朱雀"


def test_bian_gua_uses_own_palace():
    """乾为天三爻动 → 天泽履（艮宫），变卦六亲按变卦自身之宫装。"""
    r = liuyao_from_throws([7, 7, 9, 7, 7, 7])
    ben, bian = r["ben"], r["bian"]
    assert bian.name == "天泽履"
    paipan_liuyao(ben, bian, _cal())

    assert (bian.gong, bian.gong_wuxing) == ("艮", "土")
    assert [ln.ganzhi for ln in bian.lines] == ["丁巳", "丁卯", "丁丑", "壬午", "壬申", "壬戌"]
    # 以艮土为我：巳火父母、卯木官鬼、丑土兄弟、午火父母、申金子孙、戌土兄弟
    assert [ln.liuqin for ln in bian.lines] == ["父母", "官鬼", "兄弟", "父母", "子孙", "兄弟"]
    # 变卦不装世应、六神
    assert not any(ln.is_shi or ln.is_ying for ln in bian.lines)
    assert all(ln.liushen == "" for ln in bian.lines)


def test_shiyao_not_installed_on_hidden_trigram_hexagrams():
    """非八纯卦的世位按宫次序推：地雷复为一世（世初应四）。"""
    ben = liuyao_from_throws([7, 8, 8, 8, 8, 8])["ben"]
    assert ben.name == "地雷复"
    paipan_liuyao(ben, None, _cal())
    assert (ben.gong, ben.shi_pos, ben.ying_pos) == ("坤", 1, 4)


@pytest.mark.parametrize(
    "ti,yong,relation,judgement",
    [
        ("坎", "乾", "用生体", "吉"),    # 金生水
        ("乾", "乾", "体用比和", "顺遂"),
        ("乾", "震", "体克用", "小吉"),  # 金克木
        ("乾", "离", "用克体", "凶"),    # 火克金
        ("乾", "坎", "体生用", "耗泄"),  # 金生水
    ],
)
def test_ti_yong_relations(ti, yong, relation, judgement):
    r = evaluate_ti_yong(ti, yong)
    assert r["relation"] == relation
    assert r["judgement"] == judgement


def test_meihua_summary_yingqi():
    s = meihua_summary("乾", "坎")
    assert s["ti_wuxing"] == "金"
    assert s["yingqi"] == "申酉"
