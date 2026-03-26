"""data_quality / leakage_guard 向けのスキーマ土台（未実装フィールドは後から追加）。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DataQualityContext(BaseModel):
    """検証時コンテキスト。レコード種別・パイプライン段階などを後で足す。"""

    model_config = ConfigDict(extra="allow")

    source: str = Field(default="unknown", description="データソース識別子")
    notes: str | None = None


class DataQualityIssue(BaseModel):
    """単一の品質 issue。ルール ID や重大度は後続で拡張。"""

    model_config = ConfigDict(extra="allow")

    code: str = Field(default="UNSPECIFIED", description="ルール／理由コード")
    message: str = ""
    field: str | None = None


class DataQualityReport(BaseModel):
    """data_quality 集約結果。"""

    model_config = ConfigDict(extra="forbid")

    issues: list[DataQualityIssue] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.issues) == 0


class LeakageContext(BaseModel):
    """リーク検査用コンテキスト（時系列境界・スプリット ID 等を後で追加）。"""

    model_config = ConfigDict(extra="allow")

    split_id: str | None = None
    as_of: str | None = None


class LeakageFinding(BaseModel):
    """リーク疑いの1件。"""

    model_config = ConfigDict(extra="allow")

    code: str = Field(default="UNSPECIFIED")
    message: str = ""
    feature: str | None = None


class LeakageGuardReport(BaseModel):
    """leakage_guard 集約結果。"""

    model_config = ConfigDict(extra="forbid")

    findings: list[LeakageFinding] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.findings) == 0


class RecordPayload(BaseModel):
    """検証対象の汎用レコード入れ物（中身は実装フェーズで差し替え）。"""

    model_config = ConfigDict(extra="allow")

    kind: str = Field(default="generic", description="レコード種別")
    data: dict[str, Any] = Field(default_factory=dict)
