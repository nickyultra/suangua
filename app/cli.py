# -*- coding: utf-8 -*-
"""命令行入口。

无 API Key 也能出完整排盘；配了 key 才附解读。
  python -m app.cli -q "今年财运如何" -m liuyao
  python -m app.cli -q "感情" -m meihua_number -n 7 13
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from .config import get_settings
from .core.models import DivinationResult, Gua
from .pipeline import (
    MODE_LABELS,
    MODE_LIUYAO,
    MODE_MEIHUA_NUMBER,
    MODE_MEIHUA_TIME,
    build_result,
)


def _gua_lines(gua: Gua, *, six_relation: bool) -> list[str]:
    rows = []
    for ln in reversed(gua.lines):  # 上爻在前
        left = f"{ln.liushen:<2}" if ln.liushen else "  "
        najia = f"{ln.ganzhi}{ln.wuxing}" if ln.ganzhi else ""
        liuqin = ln.liuqin if six_relation else ""
        tags = []
        if ln.is_shi:
            tags.append("世")
        if ln.is_ying:
            tags.append("应")
        if ln.moving:
            tags.append("动")
        if ln.kong:
            tags.append("空")
        rows.append(
            f"  {left} {najia:<5} {liuqin:<4} {ln.symbol:<10} {' '.join(tags)}"
        )
    return rows


def render(result: DivinationResult) -> str:
    cal = result.calendar
    out = [
        f"【起卦方式】{MODE_LABELS.get(result.mode, result.mode)}",
        f"【占问事项】{result.question or '（未填写）'}   [{result.matter}"
        + (f" / {result.gender}" if result.gender else "")
        + "]",
        f"【起卦时间】公历 {cal.solar_text}｜农历 {cal.lunar_text}",
        f"            {cal.year_gz}年 {cal.month_gz}月 {cal.day_gz}日 {cal.hour_gz}时",
        f"【月建】{cal.month_jian}　【日辰】{cal.day_chen}　【旬空】{cal.xun}旬空{cal.xun_kong}",
        "",
    ]

    is_liuyao = result.mode == MODE_LIUYAO
    ben = result.ben
    head = f"本卦 {ben.full_name}　{ben.symbol}"
    if is_liuyao:
        head += f"　宫{ben.gong}{ben.gong_wuxing}　世{ben.shi_pos}应{ben.ying_pos}"
    out.append(head)
    out += _gua_lines(ben, six_relation=is_liuyao)

    if result.bian is not None:
        out.append("")
        head = f"变卦 {result.bian.full_name}　{result.bian.symbol}"
        if is_liuyao and result.bian.gong:
            head += f"　宫{result.bian.gong}{result.bian.gong_wuxing}"
        out.append(head)
        out += _gua_lines(result.bian, six_relation=is_liuyao)

    if result.mode == MODE_LIUYAO:
        pos = result.yongshen_pos
        out.append("")
        out.append(
            f"用神：{result.yongshen}"
            + (f"（{ '、'.join(f'{p}爻' for p in pos)}）" if pos else "（用神不上卦）")
        )
    else:
        out.append("")
        out.append(f"互卦：{result.hu.full_name if result.hu else '—'}")
        out.append(
            f"体用：体{result.ti}　用{result.yong}　{result.ti_yong_relation}"
            f"（{result.tiyong_detail.get('judgement', '')}）"
        )
        out.append(f"应期参考：{result.tiyong_detail.get('yingqi', '')}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="易学占卜（本地命令行）")
    parser.add_argument("-q", "--question", default="", help="占问之事")
    parser.add_argument(
        "-m", "--mode",
        default=MODE_LIUYAO,
        choices=[MODE_LIUYAO, MODE_MEIHUA_NUMBER, MODE_MEIHUA_TIME],
        help="起卦方式",
    )
    parser.add_argument("-n", "--numbers", nargs=2, type=int, help="梅花报数（两个 1–99）")
    parser.add_argument("--matter", default="self", help="事项枚举，默认 self")
    parser.add_argument("--gender", default="", choices=["", "男", "女"])
    parser.add_argument("--at", default="", help="指定时间 YYYY-MM-DD HH:MM")
    parser.add_argument("--no-llm", action="store_true", help="只出排盘，不调用模型")
    args = parser.parse_args(argv)

    moment = (
        datetime.strptime(args.at, "%Y-%m-%d %H:%M") if args.at else datetime.now()
    )
    settings = get_settings()

    result = build_result(
        question=args.question,
        mode=args.mode,
        matter=args.matter,
        gender=args.gender,
        moment=moment,
        numbers=tuple(args.numbers) if args.numbers else None,
        sect=settings.day_boundary_sect,
    )
    print(render(result))

    if args.no_llm or not settings.llm_ready:
        if not settings.llm_ready and not args.no_llm:
            print("\n（未配置 LLM_API_KEY，仅输出排盘）")
        return 0

    from .llm.client import interpret_stream

    print("\n" + "─" * 60)
    try:
        for piece in interpret_stream(result, settings):
            sys.stdout.write(piece)
            sys.stdout.flush()
    except Exception as exc:  # noqa: BLE001 - 命令行需要直观报错
        print(f"\n[解读失败] {exc}")
        return 1
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
