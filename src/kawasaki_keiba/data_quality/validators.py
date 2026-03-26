"""データ品質バリデーション

入力データの整合性・欠損・異常値を検出する。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class ValidationResult:
    """バリデーション結果"""
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


def validate_race_entries(df: pd.DataFrame) -> ValidationResult:
    """出走表データのバリデーション"""
    errors: list[str] = []
    warnings: list[str] = []
    stats: dict[str, Any] = {}

    required_cols = [
        "race_id", "horse_id", "horse_number", "jockey_id",
        "weight_carried", "distance", "race_date",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        errors.append(f"必須列が不足: {missing}")
        return ValidationResult(is_valid=False, errors=errors)

    # 重複チェック
    dup = df.duplicated(subset=["race_id", "horse_number"], keep=False)
    if dup.any():
        errors.append(f"race_id + horse_number に重複あり: {dup.sum()} 行")

    # 欠損率
    null_rates = df[required_cols].isnull().mean()
    for col, rate in null_rates.items():
        if rate > 0:
            warnings.append(f"{col} 欠損率: {rate:.1%}")
    stats["null_rates"] = null_rates.to_dict()

    # 馬番範囲
    if (df["horse_number"] < 1).any() or (df["horse_number"] > 16).any():
        errors.append("horse_number が 1-16 の範囲外")

    # 距離範囲（川崎は 900m - 2100m）
    if "distance" in df.columns:
        invalid_dist = (df["distance"] < 900) | (df["distance"] > 2100)
        if invalid_dist.any():
            warnings.append(f"川崎競馬の距離範囲外: {df.loc[invalid_dist, 'distance'].unique()}")

    stats["num_races"] = df["race_id"].nunique()
    stats["num_entries"] = len(df)

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        stats=stats,
    )


def validate_results(df: pd.DataFrame) -> ValidationResult:
    """レース結果データのバリデーション"""
    errors: list[str] = []
    warnings: list[str] = []

    required_cols = ["race_id", "horse_id", "horse_number", "finish_position"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        errors.append(f"必須列が不足: {missing}")
        return ValidationResult(is_valid=False, errors=errors)

    # 着順の連続性チェック（各レース内で1から連続）
    for race_id, group in df.groupby("race_id"):
        positions = sorted(group["finish_position"].dropna().astype(int).tolist())
        expected = list(range(1, len(positions) + 1))
        if positions != expected:
            warnings.append(f"{race_id}: 着順が不連続 {positions}")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
