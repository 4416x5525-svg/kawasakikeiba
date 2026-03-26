"""data_quality / leakage_guard の呼び出し口（中身は後続実装）。"""

from __future__ import annotations

from kawasaki_ai.utils.schema import (
    DataQualityContext,
    DataQualityReport,
    LeakageContext,
    LeakageGuardReport,
    RecordPayload,
)


def validate_data_quality(
    record: RecordPayload,
    *,
    ctx: DataQualityContext | None = None,
) -> DataQualityReport:
    """データ品質チェック。現状は常に空の report（ルールは後で注入）。"""
    _ = ctx
    _ = record
    return DataQualityReport()


def check_leakage_guard(
    record: RecordPayload,
    *,
    ctx: LeakageContext | None = None,
) -> LeakageGuardReport:
    """リークガード。現状は常に空の report（ルールは後で注入）。"""
    _ = ctx
    _ = record
    return LeakageGuardReport()
