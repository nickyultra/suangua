# -*- coding: utf-8 -*-
"""运行配置。全部可由 .env 或环境变量覆盖。"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ── 模型（OpenAI 兼容）──────────────────────────────
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.8
    llm_timeout: float = 120.0

    # ── 历法 ────────────────────────────────────────────
    # 晚子时（23:00–23:59）日柱流派：1=算次日，2=算当天
    day_boundary_sect: int = 2

    # ── 服务 ────────────────────────────────────────────
    host: str = "127.0.0.1"
    port: int = 8000

    @property
    def llm_ready(self) -> bool:
        return bool(self.llm_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
