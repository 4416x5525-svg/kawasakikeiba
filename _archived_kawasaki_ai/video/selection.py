"""映像レビュー対象馬の選定雛形（アルゴリズム本体は未実装）。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewCandidate:
    """出走馬1頭のメタ（映像レビュー優先度の入力）。"""

    horse_id: str
    horse_number: int
    popularity_rank: int | None = None
    core_rank: int | None = None


def select_race_video_review_targets(
    candidates: Sequence[ReviewCandidate],
    *,
    max_horses: int = 4,
) -> tuple[str, ...]:
    """レビュー対象の horse_id を選ぶ雛形。

    現状ロジック:
    - `popularity_rank` がある馬を先に（数値が小さいほど優先）、同順位は `horse_number` 昇順
    - 人気なしは後ろに回し、`horse_number` 昇順
    - 先頭から最大 `max_horses` 頭

    `core_rank` は現状ソートに使わない（将来の合成スコア用フィールド）。

    TODO（後続で差し替え）:
    - Core 順位・Gate 関心・人気ベースラインとの距離などを合成したスコア
    - 少頭数／取消後のクォータ調整
    - 同一優先度のタイブレーク方針の設定化
    """
    if max_horses < 1:
        msg = "max_horses must be >= 1"
        raise ValueError(msg)
    items = list(candidates)

    def sort_key(c: ReviewCandidate) -> tuple[int, int, int, str]:
        if c.popularity_rank is not None:
            return (0, c.popularity_rank, c.horse_number, c.horse_id)
        return (1, c.horse_number, 0, c.horse_id)

    items.sort(key=sort_key)
    return tuple(c.horse_id for c in items[:max_horses])
