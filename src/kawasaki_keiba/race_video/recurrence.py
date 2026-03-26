"""主タグの再発度（kawasaki_keiba.race_video）。映像解析は行わない。

パイプライン（固定）:
  1. history_newest_last の末尾から window 件を窓とする（時系列は古→新、最後が最新）
  2. None を除き、tag と一致する件数を hits とする
  3. hits を閾値で離散化: hits >= high_at → HIGH, hits >= medium_at → MEDIUM, それ以外 LOW

既定閾値: medium_at=2, high_at=3（設定化は呼び出し側の引数で）。
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum

from .race_tags import MainRaceTag

MainTagHistory = Sequence[MainRaceTag | None]

DEFAULT_RECURRENCE_WINDOW: int = 5
DEFAULT_RECURRENCE_MEDIUM_AT: int = 2
DEFAULT_RECURRENCE_HIGH_AT: int = 3


class RecurrenceLevel(StrEnum):
    """再発度の3段階（hits から機械的に決定）。"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def recurrence_level_from_hit_count(
    hits: int,
    *,
    medium_at: int = DEFAULT_RECURRENCE_MEDIUM_AT,
    high_at: int = DEFAULT_RECURRENCE_HIGH_AT,
) -> RecurrenceLevel:
    """非負整数 hits を閾値で LOW / MEDIUM / HIGH に分類する。"""
    if hits < 0:
        msg = "hits must be non-negative"
        raise ValueError(msg)
    if medium_at < 1 or high_at < medium_at:
        msg = "invalid thresholds"
        raise ValueError(msg)
    if hits >= high_at:
        return RecurrenceLevel.HIGH
    if hits >= medium_at:
        return RecurrenceLevel.MEDIUM
    return RecurrenceLevel.LOW


def count_main_tag_in_window(
    tag: MainRaceTag,
    history_newest_last: MainTagHistory,
    *,
    window: int,
) -> int:
    """窓内の tag 一致回数（None は無視）。"""
    if window < 1:
        msg = "window must be >= 1"
        raise ValueError(msg)
    slice_ = history_newest_last[-window:]
    return sum(1 for t in slice_ if t is not None and t == tag)


def recurrence_level_for_main_tag(
    tag: MainRaceTag,
    history_newest_last: MainTagHistory,
    *,
    window: int = DEFAULT_RECURRENCE_WINDOW,
    medium_at: int = DEFAULT_RECURRENCE_MEDIUM_AT,
    high_at: int = DEFAULT_RECURRENCE_HIGH_AT,
) -> RecurrenceLevel:
    """count → recurrence_level_from_hit_count の合成。"""
    hits = count_main_tag_in_window(tag, history_newest_last, window=window)
    return recurrence_level_from_hit_count(hits, medium_at=medium_at, high_at=high_at)
