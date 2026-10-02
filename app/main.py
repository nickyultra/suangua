# -*- coding: utf-8 -*-
"""FastAPI 应用：起卦排盘接口 + 流式解卦接口 + 静态页面。"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .api.schemas import DivineRequest, DivineResponse, MetaResponse
from .config import Settings, get_settings
from .core.constants import MATTER_LABELS
from .llm.client import LLMNotConfigured, classify, interpret_stream
from .pipeline import MODE_LABELS, MODES, build_result

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="易学占卜", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ── 页面 ─────────────────────────────────────────────────────────────


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/meta", response_model=MetaResponse)
def meta() -> MetaResponse:
    s = get_settings()
    return MetaResponse(
        modes=[{"value": m, "label": MODE_LABELS[m]} for m in MODES],
        matters=[{"value": k, "label": v} for k, v in MATTER_LABELS.items()],
        llm_ready=s.llm_ready,
        model=s.llm_model,
        sect=s.day_boundary_sect,
    )


# ── N1 事项判定 ──────────────────────────────────────────────────────


def _resolve_matter(
    req: DivineRequest, settings: Settings
) -> tuple[str, str, bool, list[str]]:
    """返回 (matter, gender, 是否自动判定, 提示信息)。"""
    if req.matter != "auto":
        return req.matter, req.gender, False, []

    if not settings.llm_ready:
        return (
            "self",
            req.gender,
            True,
            ["未配置模型，事项暂按「自身」处理；可在表单里手动指定事项。"],
        )
    try:
        got = classify(req.question, settings)
        return got["matter"], got["gender"] or req.gender, True, []
    except Exception as exc:  # noqa: BLE001 - 分类失败不应阻断排盘
        return "self", req.gender, True, [f"自动判定事项失败（{exc}），暂按「自身」处理。"]


def _prepare(req: DivineRequest, settings: Settings):
    matter, gender, auto, notices = _resolve_matter(req, settings)
    try:
        result = build_result(
            question=req.question,
            mode=req.mode,
            matter=matter,
            gender=gender,
            moment=req.parsed_moment(),
            numbers=req.parsed_numbers(),
            throws=req.throws,
            sect=settings.day_boundary_sect,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result, matter, gender, auto, notices


# ── N2–N6 起卦排盘 ───────────────────────────────────────────────────


@app.post("/api/divine", response_model=DivineResponse)
def divine(req: DivineRequest) -> DivineResponse:
    settings = get_settings()
    result, matter, gender, auto, notices = _prepare(req, settings)
    return DivineResponse(
        result=result.to_dict(),
        matter=matter,
        gender=gender,
        matter_auto=auto,
        llm_ready=settings.llm_ready,
        notices=notices,
    )


# ── N7 流式解卦 ──────────────────────────────────────────────────────


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.post("/api/interpret")
def interpret(req: DivineRequest) -> StreamingResponse:
    settings = get_settings()
    result, matter, gender, auto, notices = _prepare(req, settings)

    def stream():
        for note in notices:
            yield _sse({"notice": note})
        if not settings.llm_ready:
            yield _sse({"error": "未配置模型，无法解读。请在 .env 中填入 LLM_API_KEY 后重启。"})
            return
        try:
            for piece in interpret_stream(result, settings):
                yield _sse({"text": piece})
        except LLMNotConfigured as exc:
            yield _sse({"error": str(exc)})
        except Exception as exc:  # noqa: BLE001 - 流已开始，只能以事件回报
            yield _sse({"error": f"解读失败：{exc}"})
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def main() -> None:
    import uvicorn

    s = get_settings()
    uvicorn.run("app.main:app", host=s.host, port=s.port, reload=False)


if __name__ == "__main__":
    main()
