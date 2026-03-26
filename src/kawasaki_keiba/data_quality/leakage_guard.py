"""リーケージガード

未来情報の混入を防止する。時系列分割の管理を行う。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass
class TimeSeriesSplit:
    """時系列分割の定義

    ランダム分割は禁止。必ず時系列で分割する。
    train_end < val_start <= val_end < test_start を保証する。
    """
    train_start: date
    train_end: date
    val_start: date
    val_end: date
    test_start: date
    test_end: date

    def __post_init__(self) -> None:
        if not (self.train_start <= self.train_end
                < self.val_start <= self.val_end
                < self.test_start <= self.test_end):
            raise ValueError(
                "時系列分割の順序が不正: "
                f"train=[{self.train_start}, {self.train_end}], "
                f"val=[{self.val_start}, {self.val_end}], "
                f"test=[{self.test_start}, {self.test_end}]"
            )

    def split(self, df: pd.DataFrame, date_col: str = "race_date") -> tuple[
        pd.DataFrame, pd.DataFrame, pd.DataFrame
    ]:
        """DataFrameを train/val/test に分割する"""
        dates = pd.to_datetime(df[date_col]).dt.date
        train = df[(dates >= self.train_start) & (dates <= self.train_end)]
        val = df[(dates >= self.val_start) & (dates <= self.val_end)]
        test = df[(dates >= self.test_start) & (dates <= self.test_end)]
        return train, val, test


def check_feature_leakage(
    features_df: pd.DataFrame,
    target_df: pd.DataFrame,
    date_col: str = "race_date",
    join_key: str = "race_id",
) -> list[str]:
    """特徴量に未来情報が混入していないかチェックする

    各行について、特徴量の元データの日付が
    対象レースの日付より後でないことを確認する。

    Returns:
        リーケージが疑われる列名のリスト
    """
    warnings: list[str] = []

    # 結果データの列が特徴量に含まれていないか
    result_only_cols = {"finish_position", "finish_time", "payout", "profit"}
    leaked = result_only_cols & set(features_df.columns)
    if leaked:
        warnings.append(f"結果列が特徴量に含まれている: {leaked}")

    # オッズが確定オッズの場合の警告
    if "odds_win" in features_df.columns:
        warnings.append(
            "odds_win が特徴量に含まれている: "
            "確定オッズは結果確定後の値であり、リーケージの可能性あり。"
            "締切前オッズを使う場合は列名を odds_win_pre_close 等にして区別すること"
        )

    return warnings


FORBIDDEN_FEATURES_AT_PREDICTION_TIME = frozenset({
    "finish_position",
    "finish_time",
    "margin",
    "last_3f",
    "corner_positions",
    "payout",
    "profit",
    "result_position",
})
"""予測時点では絶対に使ってはいけない列"""


def assert_no_forbidden_features(df: pd.DataFrame) -> None:
    """予測時特徴量に禁止列が含まれていないことを確認する"""
    found = FORBIDDEN_FEATURES_AT_PREDICTION_TIME & set(df.columns)
    if found:
        raise ValueError(f"予測時禁止列が含まれている: {found}")
