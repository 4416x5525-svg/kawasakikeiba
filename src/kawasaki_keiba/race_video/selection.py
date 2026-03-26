"""映像レビュー対象馬の選抜（kawasaki_keiba.race_video）。アルゴリズム本体は未実装。

選抜ルール（現行・読み順）:
  1. 人気あり（popularity_rank が int）を人気なしより先に並べる
  2. 人気あり群内: popularity_rank 昇順（1 人気が最優先）
  3. 同じ人気順位では horse_number 昇順
  4. 人気なし群内: horse_number 昇順
  5. 最終タイブレーク: horse_id の辞書順
  6. 先頭から max_horses 頭の horse_id を返す

core_rank は将来の合成キー用フィールド（現状ソートに未使用）。
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewCandidate:
    """1頭分の選抜入力。"""

    horse_id: str
    horse_number: int
    popularity_rank: int | None = None
    core_rank: int | None = None


def _review_sort_key(candidate: ReviewCandidate) -> tuple[int, int, int, str]:
    """ルール 1–5 に対応するソートキー（昇順＝優先）。"""
    if candidate.popularity_rank is not None:
        return (0, candidate.popularity_rank, candidate.horse_number, candidate.horse_id)
    return (1, candidate.horse_number, 0, candidate.horse_id)


def select_race_video_review_targets(
    candidates: Iterable[ReviewCandidate],
    *,
    max_horses: int = 4,
) -> tuple[str, ...]:
    """選抜ルールに従い horse_id のタプルを返す。"""
    if max_horses < 1:
        msg = "max_horses must be >= 1"
        raise ValueError(msg)
    ordered = sorted(candidates, key=_review_sort_key)
    return tuple(c.horse_id for c in ordered[:max_horses])
