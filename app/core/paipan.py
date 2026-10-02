# -*- coding: utf-8 -*-
"""N5 排盘。

六爻：纳甲、八宫归属、世应、六亲、六神、旬空。
梅花：体用、体用生克断语、应期参考。
"""

from __future__ import annotations

from .constants import (
    GONG_WUXING,
    GUA_GONG,
    LIUSHEN,
    LIUSHEN_START,
    NAJIA,
    SHI_POS,
    YING_POS,
    ZHI,
    ZHI_WUXING,
    wuxing_relation,
)
from .models import CalendarInfo, Gua

# 变卦六亲是否以变卦自身之宫为准（多数排盘软件的做法）。
# 置 False 则沿用本卦之宫。
BIAN_GUA_OWN_GONG = True

_REL_TO_LIUQIN = {
    "生我": "父母",
    "我生": "子孙",
    "克我": "官鬼",
    "我克": "妻财",
    "同我": "兄弟",
}

# 梅花应期：以五行所属地支为期（知识库 4.4）
YINGQI = {
    "金": "申酉",
    "木": "寅卯",
    "水": "亥子",
    "火": "巳午",
    "土": "辰戌丑未",
}


# ── 六爻 ─────────────────────────────────────────────────────────────


def set_najia(gua: Gua) -> None:
    """按纳甲歌装干支。阳卦顺行、阴卦逆行。"""
    for tri, positions, outer in (
        (gua.lower, (1, 2, 3), False),
        (gua.upper, (4, 5, 6), True),
    ):
        gan_in, zhi_in, gan_out, zhi_out, step = NAJIA[tri]
        gan, first_zhi = (gan_out, zhi_out) if outer else (gan_in, zhi_in)
        start = ZHI.index(first_zhi)
        for k, pos in enumerate(positions):
            zhi = ZHI[(start + step * k) % 12]
            line = gua.lines[pos - 1]
            line.gan = gan
            line.zhi = zhi
            line.wuxing = ZHI_WUXING[zhi]


def set_gong(gua: Gua) -> None:
    gua.gong = GUA_GONG[gua.name]
    gua.gong_wuxing = GONG_WUXING[gua.gong]


def set_liuqin(gua: Gua, gong_wuxing: str) -> None:
    """以宫五行为「我」定六亲。"""
    for line in gua.lines:
        rel = wuxing_relation(gong_wuxing, line.wuxing)
        line.liuqin = _REL_TO_LIUQIN[rel]


def set_shi_ying(gua: Gua) -> None:
    gua.shi_pos = SHI_POS[gua.name]
    gua.ying_pos = YING_POS[gua.name]
    gua.lines[gua.shi_pos - 1].is_shi = True
    gua.lines[gua.ying_pos - 1].is_ying = True


def set_liushen(gua: Gua, day_gan: str) -> None:
    """六神按日干起，自初爻排起。"""
    start = LIUSHEN_START[day_gan]
    for i, line in enumerate(gua.lines):
        line.liushen = LIUSHEN[(start + i) % 6]


def set_kong(gua: Gua, xun_kong: str) -> None:
    for line in gua.lines:
        line.kong = line.zhi in xun_kong


def paipan_liuyao(ben: Gua, bian: Gua | None, cal: CalendarInfo) -> None:
    """就地为本卦装卦；变卦只装纳甲与六亲（不装世应、六神）。"""
    set_najia(ben)
    set_gong(ben)
    set_liuqin(ben, ben.gong_wuxing)
    set_shi_ying(ben)
    set_liushen(ben, cal.day_gz[0])
    set_kong(ben, cal.xun_kong)

    if bian is not None:
        set_najia(bian)
        set_gong(bian)
        set_liuqin(bian, bian.gong_wuxing if BIAN_GUA_OWN_GONG else ben.gong_wuxing)
        set_kong(bian, cal.xun_kong)


# ── 梅花 ─────────────────────────────────────────────────────────────


def evaluate_ti_yong(ti: str, yong: str) -> dict:
    """按知识库 4.3 判体用生克。ti/yong 为八卦名。"""
    from .constants import BAGUA_WUXING

    ti_wx, yong_wx = BAGUA_WUXING[ti], BAGUA_WUXING[yong]
    rel = wuxing_relation(ti_wx, yong_wx)  # 以「体」为我

    if rel == "生我":
        return {"relation": "用生体", "judgement": "吉", "note": "事来就我，有人相助"}
    if rel == "同我":
        return {"relation": "体用比和", "judgement": "顺遂", "note": "可成"}
    if rel == "我克":
        return {"relation": "体克用", "judgement": "小吉", "note": "我能制事，但需费力"}
    if rel == "克我":
        return {"relation": "用克体", "judgement": "凶", "note": "事来克我，有阻难"}
    return {"relation": "体生用", "judgement": "耗泄", "note": "我去就事，劳心费力、有损耗"}


def meihua_summary(ti: str, yong: str) -> dict:
    from .constants import BAGUA_WUXING

    result = evaluate_ti_yong(ti, yong)
    result["ti_wuxing"] = BAGUA_WUXING[ti]
    result["yong_wuxing"] = BAGUA_WUXING[yong]
    result["yingqi"] = YINGQI[BAGUA_WUXING[ti]]
    return result
