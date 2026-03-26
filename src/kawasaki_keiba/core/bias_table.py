"""Historical Bias: 過去データから距離群×馬場群×頭数帯の構造的偏りを算出する。

Core の特徴量 F6/F7 として使用。独立モジュールではなく Core 内部に配置。
Track Bias（当日リアルタイム）との違い:
  - Historical Bias は事前計算（オフライン）
  - 数百〜数千レースの集計に基づく
  - 変化が遅い（コース改修まで持続）
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from kawasaki_keiba.schemas.race import HorseEntry, RaceRecord, RaceResult, TrackCondition

# 最低サンプル数
MIN_RACES_PER_CELL = 15
# 少頭数レースは除外
MIN_RUNNERS = 6


def _distance_group(distance: int) -> str:
    """距離を3群に分類。"""
    if distance <= 1000:
        return "short"
    if distance <= 1600:
        return "mid"
    return "long"


def _condition_group(condition: TrackCondition) -> str:
    """馬場を2群に分類。"""
    if condition in (TrackCondition.GOOD, TrackCondition.SLIGHTLY_HEAVY):
        return "good"
    return "heavy"


def _field_group(num_runners: int) -> str:
    """頭数を2群に分類。"""
    return "small" if num_runners <= 6 else "normal"


@dataclass(frozen=True)
class BiasCell:
    """1条件セルの統計値。

    Attributes:
        distance_group: "short" | "mid" | "long"
        condition_group: "good" | "heavy"
        field_size_group: "small" | "normal"
        inner_win_rate: 内枠(1-4番)の勝率
        outer_win_rate: 外枠(9+番)の勝率
        inner_advantage: inner_win_rate - outer_win_rate (正=内有利)
        front_place_rate: 先行勢の複勝率
        closer_place_rate: 差し勢の複勝率
        pace_advantage: front - closer (正=先行有利)
        sample_races: サンプルレース数
        sample_period: データ期間
        significant_post: 枠番バイアスが統計的に有意か
        significant_pace: 脚質バイアスが統計的に有意か
    """

    distance_group: str
    condition_group: str
    field_size_group: str
    inner_win_rate: float
    outer_win_rate: float
    inner_advantage: float
    front_place_rate: float
    closer_place_rate: float
    pace_advantage: float
    sample_races: int
    sample_period: str
    significant_post: bool
    significant_pace: bool

    @property
    def confidence(self) -> float:
        """サンプル数ベースの信頼度 [0, 1]。"""
        if self.sample_races < MIN_RACES_PER_CELL:
            return 0.0
        return min(1.0, self.sample_races / 200)

    def to_score(self) -> float:
        """[-2, 2] 帯域のスコア。"""
        post = self.inner_advantage if self.significant_post else 0.0
        pace = self.pace_advantage if self.significant_pace else 0.0
        raw = (post + pace) * self.confidence
        return max(-2.0, min(2.0, raw * 10.0))

    def short_reason(self) -> str:
        parts: list[str] = []
        if self.significant_post:
            if self.inner_advantage > 0:
                parts.append(f"内枠有利(+{self.inner_advantage:.1%})")
            else:
                parts.append(f"外枠有利({self.inner_advantage:.1%})")
        if self.significant_pace:
            if self.pace_advantage > 0:
                parts.append(f"先行有利(+{self.pace_advantage:.1%})")
            else:
                parts.append(f"差し有利({self.pace_advantage:.1%})")
        if not parts:
            return f"有意な傾向なし(n={self.sample_races})"
        return "・".join(parts) + f" (n={self.sample_races})"

    def to_dict(self) -> dict[str, object]:
        return {
            "distance_group": self.distance_group,
            "condition_group": self.condition_group,
            "field_size_group": self.field_size_group,
            "inner_win_rate": round(self.inner_win_rate, 4),
            "outer_win_rate": round(self.outer_win_rate, 4),
            "inner_advantage": round(self.inner_advantage, 4),
            "front_place_rate": round(self.front_place_rate, 4),
            "closer_place_rate": round(self.closer_place_rate, 4),
            "pace_advantage": round(self.pace_advantage, 4),
            "sample_races": self.sample_races,
            "sample_period": self.sample_period,
            "significant_post": self.significant_post,
            "significant_pace": self.significant_pace,
            "confidence": round(self.confidence, 3),
            "score": round(self.to_score(), 3),
            "short_reason": self.short_reason(),
        }


CellKey = tuple[str, str, str]  # (distance_group, condition_group, field_size_group)


def _parse_corners(s: str | None) -> list[int] | None:
    if not s:
        return None
    try:
        return [int(x.strip()) for x in s.split("-") if x.strip()]
    except ValueError:
        return None


def build_bias_table(
    races: list[RaceRecord],
    all_entries: dict[str, list[HorseEntry]],
    all_results: dict[str, list[RaceResult]],
    *,
    min_date: date | None = None,
    significance_threshold: float = 0.03,
    min_races_per_cell: int | None = None,
) -> dict[CellKey, BiasCell]:
    """過去データからバイアステーブルを構築する。

    Args:
        races: 全レースリスト
        all_entries: {race_id: [HorseEntry]}
        all_results: {race_id: [RaceResult]}
        min_date: この日付以降のデータのみ使用（コース改修対応）
        significance_threshold: 勝率差がこれ以上なら有意と判定
        min_races_per_cell: セルを出力する最小レース数。None のとき ``MIN_RACES_PER_CELL``
            （15）。loader の 10R サンプルでセルを得る検証には 6 程度を指定する。
    """
    threshold_races = (
        MIN_RACES_PER_CELL if min_races_per_cell is None else max(1, min_races_per_cell)
    )
    # セルごとに集計（race_dates は ISO 文字列）
    cell_data: dict[CellKey, dict[str, Any]] = {}

    for race in races:
        if min_date and race.race_date < min_date:
            continue
        if race.num_runners < MIN_RUNNERS:
            continue

        entries = all_entries.get(race.race_id, [])
        results = all_results.get(race.race_id, [])
        if not entries or not results:
            continue

        key: CellKey = (
            _distance_group(race.distance),
            _condition_group(race.track_condition),
            _field_group(race.num_runners),
        )
        if key not in cell_data:
            cell_data[key] = {
                "inner_wins": [], "outer_wins": [],
                "front_places": [], "closer_places": [],
                "race_dates": [],
            }

        result_map = {r.horse_number: r for r in results}
        mid = race.num_runners / 2

        for entry in entries:
            res = result_map.get(entry.horse_number)
            if res is None:
                continue

            is_winner = res.finish_position == 1
            is_placed = res.finish_position <= 3

            if entry.post_position <= mid:
                cell_data[key]["inner_wins"].append(1.0 if is_winner else 0.0)
            elif entry.post_position > mid + 2:  # 明確な外枠
                cell_data[key]["outer_wins"].append(1.0 if is_winner else 0.0)

            # 脚質判定（corner_positions の最初の値）
            corners = _parse_corners(res.corner_positions)
            if corners and len(corners) >= 1:
                third = max(1, race.num_runners // 3)
                if corners[0] <= third:
                    cell_data[key]["front_places"].append(1.0 if is_placed else 0.0)
                elif corners[0] >= race.num_runners - third + 1:
                    cell_data[key]["closer_places"].append(1.0 if is_placed else 0.0)

        cell_data[key]["race_dates"].append(race.race_date.isoformat())

    # セルごとに BiasCell を構築
    table: dict[CellKey, BiasCell] = {}

    for key, data in cell_data.items():
        inner_w: list[float] = data["inner_wins"]
        outer_w: list[float] = data["outer_wins"]
        front_p: list[float] = data["front_places"]
        closer_p: list[float] = data["closer_places"]
        dates: list[str] = data["race_dates"]

        n_races = len(dates)
        if n_races < threshold_races:
            continue

        iw = sum(inner_w) / len(inner_w) if inner_w else 0.0
        ow = sum(outer_w) / len(outer_w) if outer_w else 0.0
        fp = sum(front_p) / len(front_p) if front_p else 0.0
        cp = sum(closer_p) / len(closer_p) if closer_p else 0.0

        advantage_post = iw - ow
        advantage_pace = fp - cp

        period = f"{min(dates)} to {max(dates)}" if dates else ""

        table[key] = BiasCell(
            distance_group=key[0],
            condition_group=key[1],
            field_size_group=key[2],
            inner_win_rate=round(iw, 4),
            outer_win_rate=round(ow, 4),
            inner_advantage=round(advantage_post, 4),
            front_place_rate=round(fp, 4),
            closer_place_rate=round(cp, 4),
            pace_advantage=round(advantage_pace, 4),
            sample_races=n_races,
            sample_period=period,
            significant_post=abs(advantage_post) >= significance_threshold,
            significant_pace=abs(advantage_pace) >= significance_threshold,
        )

    return table


def summarize_bias_table(table: dict[CellKey, BiasCell]) -> dict[str, object]:
    """ログ・REPL 向けの最小サマリ（返り値の目視確認用）。"""
    if not table:
        return {"n_cells": 0, "max_sample_races": 0, "cells": []}
    cells: list[dict[str, object]] = []
    for key, cell in table.items():
        dg, cg, fg = key
        cells.append(
            {
                "distance_group": dg,
                "condition_group": cg,
                "field_size_group": fg,
                "sample_races": cell.sample_races,
                "inner_advantage": cell.inner_advantage,
                "pace_advantage": cell.pace_advantage,
            },
        )
    return {
        "n_cells": len(table),
        "max_sample_races": max(c.sample_races for c in table.values()),
        "cells": cells,
    }


def lookup_bias(
    table: dict[CellKey, BiasCell],
    distance: int,
    condition: TrackCondition,
    num_runners: int,
) -> BiasCell | None:
    """テーブルからバイアスセルを検索する。"""
    key: CellKey = (
        _distance_group(distance),
        _condition_group(condition),
        _field_group(num_runners),
    )
    return table.get(key)


def historical_bias_adjustment(
    cell: BiasCell | None,
    post_position: int,
    num_runners: int,
    running_style: str | None = None,
) -> float:
    """個別馬への Historical Bias 補正値 [-0.5, 0.5]。

    Core の edge 補正として使用。
    """
    if cell is None or cell.confidence < 0.1:
        return 0.0

    adj = 0.0
    mid = num_runners / 2

    if cell.significant_post:
        if post_position <= mid:
            adj += 0.15 * cell.inner_advantage * cell.confidence
        else:
            adj -= 0.15 * cell.inner_advantage * cell.confidence

    if cell.significant_pace and running_style:
        if running_style == "front":
            adj += 0.15 * cell.pace_advantage * cell.confidence
        elif running_style == "closer":
            adj -= 0.15 * cell.pace_advantage * cell.confidence

    return max(-0.5, min(0.5, adj))
