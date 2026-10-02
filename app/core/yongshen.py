# -*- coding: utf-8 -*-
"""N6 用神选取：事项 → 六亲／世应，纯查表（知识库 3.5）。"""

from __future__ import annotations

from .constants import MATTER_LABELS, MATTER_LIUQIN
from .models import Gua

VALID_MATTERS = tuple(MATTER_LIUQIN)


def normalize_matter(matter: str) -> str:
    return matter if matter in MATTER_LIUQIN else "self"


def select_yongshen(matter: str, gender: str = "") -> str:
    """返回用神：六亲名，或「世」「应」。感情类依性别定（男看妻财、女看官鬼）。"""
    matter = normalize_matter(matter)
    liuqin = MATTER_LIUQIN[matter]
    if liuqin is None:  # romance
        return "妻财" if gender == "男" else "官鬼"
    return liuqin


def locate_yongshen(gua: Gua, yongshen: str) -> list[int]:
    """用神在卦中的爻位（自初爻起，可能多现，也可能不上卦）。"""
    if yongshen == "世":
        return [gua.shi_pos]
    if yongshen == "应":
        return [gua.ying_pos]
    return [line.pos for line in gua.lines if line.liuqin == yongshen]


def matter_label(matter: str) -> str:
    return MATTER_LABELS[normalize_matter(matter)]
