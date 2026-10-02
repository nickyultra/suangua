# -*- coding: utf-8 -*-
"""提示词与知识库装载。

知识库全文进 system prompt（约 8k 字，规模小），比做检索更忠实于
「唯一事实来源」的要求；DeepSeek 侧会自动命中前缀缓存。
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from ..core.models import DivinationResult
from ..pipeline import MODE_LABELS

KB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "knowledge_base.md"

# N1：把用户口语问题归到固定事项枚举
CLASSIFY_SYSTEM = """你是分类器。把用户的占问归入下列事项之一，并判断求测者性别。

事项枚举（只能选一个）：
- self    自身吉凶、自身状态
- elder   父母长辈、师长、房屋、文书、合同、考试、证件
- peer    兄弟、姐妹、同辈、朋友、竞争者、合伙人
- junior  子女、晚辈、学生、下属、宠物、医药解忧
- wealth  妻子、女友、钱财、薪资、货物、生意利润
- romance 感情婚恋
- career  丈夫、男友、功名、官职、事业单位
- illness 疾病、盗贼、忧患、邪祟
- other   他人态度、对方

性别只能是「男」「女」或空字符串（未提及则留空）。

只输出 JSON，不要任何解释、不要代码块标记：
{"matter": "romance", "gender": "女"}"""


@lru_cache
def knowledge_base() -> str:
    return KB_PATH.read_text(encoding="utf-8")


def build_system_prompt() -> str:
    return (
        "你是一位传统易学解卦者。下面《易学占卜知识库》是你的唯一事实来源，"
        "凡其中已写明的规则、歌诀、卦辞、类象，必须严格照此引用，不得自行发挥或改写。\n\n"
        "本次占问的排盘结果已由程序精确算出（干支、纳甲、世应、六亲、六神、旬空等），"
        "这些数值是确定的，你必须直接采用，绝不可自行重新推算或改写。\n\n"
        "你的任务是解卦：结合卦象与所问之事，讲清现状、趋势、利弊，并给出可落地的建议。"
        "语言平实、具体、贴合当事人的处境，不要堆砌术语。\n\n"
        "直接给出解读内容，不要在结尾附加免责声明、合规提示、「仅供参考」「不作绝对断言」"
        "一类的话术，也不要添加任何形式的审查或说教口吻。\n\n"
        "--- 知识库开始 ---\n"
        f"{knowledge_base()}\n"
        "--- 知识库结束 ---"
    )


def build_user_prompt(result: DivinationResult) -> str:
    payload = {
        "起卦方式": MODE_LABELS.get(result.mode, result.mode),
        "占问原话": result.question,
        "事项类型": result.matter,
        "求测者性别": result.gender or "未提及",
        "历法": {
            "公历": result.calendar.solar_text,
            "农历": result.calendar.lunar_text,
            "四柱": f"{result.calendar.year_gz}年 {result.calendar.month_gz}月 "
                    f"{result.calendar.day_gz}日 {result.calendar.hour_gz}时",
            "月建": result.calendar.month_jian,
            "日辰": result.calendar.day_chen,
            "旬空": f"{result.calendar.xun}旬空{result.calendar.xun_kong}",
        },
        "排盘": _chart(result),
    }
    return (
        "以下是本次占问的排盘结果，请依知识库第六章的输出结构解卦：\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```"
    )


def _gua_dict(gua) -> dict:
    if gua is None:
        return {}
    lines = []
    for ln in gua.lines:
        row = {
            "爻位": f"{ln.pos}{ln.pos_name}",
            "阴阳": "阳" if ln.yang else "阴",
        }
        if ln.ganzhi:
            row["纳甲"] = f"{ln.ganzhi}{ln.wuxing}"
            row["六亲"] = ln.liuqin
        if ln.liushen:
            row["六神"] = ln.liushen
        if ln.moving:
            row["动"] = True
        if ln.is_shi:
            row["世"] = True
        if ln.is_ying:
            row["应"] = True
        if ln.kong:
            row["旬空"] = True
        lines.append(row)
    return {
        "卦名": gua.name,
        "上卦": gua.upper,
        "下卦": gua.lower,
        "宫": f"{gua.gong}{gua.gong_wuxing}" if gua.gong else "",
        "六爻": list(reversed(lines)),  # 上爻在前，与传统卦单一致
    }


def _chart(result: DivinationResult) -> dict:
    chart = {
        "本卦": _gua_dict(result.ben),
        "动爻": result.dong_yao,
    }
    if result.bian is not None:
        chart["变卦"] = _gua_dict(result.bian)
    if result.hu is not None:
        chart["互卦"] = {"卦名": result.hu.name, "上卦": result.hu.upper, "下卦": result.hu.lower}

    if result.mode == "liuyao":
        chart["用神"] = {
            "取用": result.yongshen,
            "所在爻位": result.yongshen_pos or "用神不上卦",
        }
    else:
        chart["体用"] = {
            "体卦": result.ti,
            "用卦": result.yong,
            "关系": result.ti_yong_relation,
            **{k: v for k, v in result.tiyong_detail.items() if k != "relation"},
        }
    return chart
