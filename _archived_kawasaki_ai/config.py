"""アプリケーション設定（拡張用の土台）。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SystemModule(StrEnum):
    """後続で実装するサブシステム。配置・CLI 拡張の共通識別子。"""

    CORE = "core"
    GATE = "gate"
    RACE_VIDEO = "race_video"
    PADDOCK = "paddock"
    WARMUP = "warmup"
    INTEGRATION = "integration"
    MONITORING = "monitoring"
    LOGGING = "logging"


class RunMode(StrEnum):
    """実行モード。"""

    DEV = "dev"
    TEST = "test"
    PROD = "prod"


class AppConfig(BaseModel):
    """seed / version / mode を保持する設定。後からフィールドを足しやすい。"""

    model_config = ConfigDict(extra="forbid", frozen=False)

    seed: int = Field(default=42, ge=0, description="再現用乱数シード")
    version: str = Field(default="0.0.0", min_length=1, description="論理バージョン")
    mode: RunMode = Field(default=RunMode.DEV, description="実行モード")
