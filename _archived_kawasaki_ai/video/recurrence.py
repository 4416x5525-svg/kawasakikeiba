"""再発度 low / medium / high の土台（履歴カウントのみ、映像解析は行わない）。"""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum

from kawasaki_ai.video.race_tags import MainRaceTag


class RecurrenceLevel(StrEnum):
    """同一主タグの再発の粗い段階。"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def recurrence_level_from_hit_count(
    hits: int,
    *,
    medium_at: int = 2,
    high_at: int = 3,
) -> RecurrenceLevel:
    """窓内の一致回数から段階を付与する（閾値は後で設定化してよい）。"""
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
    history_newest_last: Sequence[MainRaceTag | None],
    *,
    window: int,
) -> int:
    """直近 window 件（None はスキップ）のうち tag と一致する件数。"""
    if window < 1:
        msg = "window must be >= 1"
        raise ValueError(msg)
    slice_ = history_newest_last[-window:]
    return sum(1 for t in slice_ if t is not None and t == tag)


def recurrence_level_for_main_tag(
    tag: MainRaceTag,
    history_newest_last: Sequence[MainRaceTag | None],
    *,
    window: int = 5,
    medium_at: int = 2,
    high_at: int = 3,
) -> RecurrenceLevel:
    """主タグの再発度（映像解析なし・履歴のみ）。"""
    hits = count_main_tag_in_window(tag, history_newest_last, window=window)
    return recurrence_level_from_hit_count(hits, medium_at=medium_at, high_at=high_at)
