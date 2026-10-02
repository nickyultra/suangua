# -*- coding: utf-8 -*-
"""流水线 N2–N6 编排测试（不涉及 LLM）。"""

from __future__ import annotations

from datetime import datetime

import pytest

from app.pipeline import (
    MODE_LIUYAO,
    MODE_MEIHUA_NUMBER,
    MODE_MEIHUA_TIME,
    build_result,
)

MOMENT = datetime(2026, 10, 1, 14, 30)


def test_liuyao_result_is_fully_paipaned():
    r = build_result(question="事业", mode=MODE_LIUYAO, matter="career", moment=MOMENT)
    assert r.calendar.day_gz == "戊申"
    assert r.calendar.xun_kong == "寅卯"
    assert r.ben.gong  # 已装宫
    assert all(ln.ganzhi for ln in r.ben.lines)
    assert all(ln.liuqin for ln in r.ben.lines)
    assert all(ln.liushen for ln in r.ben.lines)
    assert r.ben.shi_pos and r.ben.ying_pos
    assert r.yongshen == "官鬼"
    assert r.bian is None or r.bian.lines  # 有动爻时变卦已装


def test_liuyao_yongshen_matters():
    r = build_result(question="", mode=MODE_LIUYAO, matter="wealth", moment=MOMENT)
    assert r.yongshen == "妻财"
    r = build_result(question="", mode=MODE_LIUYAO, matter="romance", gender="女", moment=MOMENT)
    assert r.yongshen == "官鬼"
    r = build_result(question="", mode=MODE_LIUYAO, matter="romance", gender="男", moment=MOMENT)
    assert r.yongshen == "妻财"
    r = build_result(question="", mode=MODE_LIUYAO, matter="self", moment=MOMENT)
    assert r.yongshen == "世"


def test_meihua_number_result():
    r = build_result(
        question="合作", mode=MODE_MEIHUA_NUMBER, numbers=(7, 13), moment=MOMENT
    )
    assert r.ben.name == "山风蛊"
    assert r.hu is not None and r.bian is not None
    assert (r.ti, r.yong) == ("艮", "巽")
    assert r.ti_yong_relation == "用克体"
    assert r.tiyong_detail["judgement"] == "凶"
    assert r.tiyong_detail["yingqi"] == "辰戌丑未"
    # 梅花不做六爻装卦
    assert all(ln.ganzhi == "" for ln in r.ben.lines)


def test_meihua_time_result():
    r = build_result(question="出行", mode=MODE_MEIHUA_TIME, moment=MOMENT)
    assert r.ben.name == "震为雷"
    assert r.ti and r.yong


def test_result_is_json_serialisable():
    import json

    r = build_result(question="测试", mode=MODE_LIUYAO, moment=MOMENT)
    data = json.loads(json.dumps(r.to_dict(), ensure_ascii=False))
    assert data["ben"]["name"] == r.ben.name
    assert len(data["ben"]["lines"]) == 6
    assert data["calendar"]["day_gz"] == "戊申"


def test_meihua_number_requires_numbers():
    with pytest.raises(ValueError):
        build_result(question="", mode=MODE_MEIHUA_NUMBER, moment=MOMENT)


def test_unknown_mode_rejected():
    with pytest.raises(ValueError):
        build_result(question="", mode="nope", moment=MOMENT)
