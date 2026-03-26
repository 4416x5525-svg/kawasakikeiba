"""Track Bias のスナップショット（1開催日×距離群の集計結果）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from kawasaki_keiba.schemas.race import TrackCondition


@dataclass(frozen=True)
class TrackBiasSnapshot:
    """当日のレース結果から算出された馬場傾向。

    Attributes:
        race_date: 開催日
        distance: 距離 (m)
        track_condition: 馬場状態
        computed_after_race: 何R目までのデータで算出したか
        post_bias: 枠番バイアス [-1,1]  負=内有利, 正=外有利
        pace_bias: 脚質バイアス [-1,1]  負=先行有利, 正=差し有利
        post_confidence: 枠番バイアスの信頼度 [0,1]
        pace_confidence: 脚質バイアスの信頼度 [0,1]
        sample_races: 算出に使ったレース数
        short_reason: 1行の人間向け説明
    """

    race_date: date
    distance: int
    track_condition: TrackCondition
    computed_after_race: int
    post_bias: float
    pace_bias: float
    post_confidence: float
    pace_confidence: float
    sample_races: int
    short_reason: str

    @property
    def bias_strength(self) -> float:
        """総合的なバイアスの強さ [0, 1]。"""
        weighted = (
            abs(self.post_bias) * self.post_confidence
            + abs(self.pace_bias) * self.pace_confidence
        )
        denom = self.post_confidence + self.pace_confidence
        if denom <= 0:
            return 0.0
        return min(1.0, weighted / denom)

    @property
    def bias_direction(self) -> str:
        """人間向けのバイアス方向サマリ。"""
        parts: list[str] = []
        if self.post_confidence >= 0.2:
            if self.post_bias < -0.2:
                parts.append("内枠有利")
            elif self.post_bias > 0.2:
                parts.append("外枠有利")
        if self.pace_confidence >= 0.2:
            if self.pace_bias < -0.2:
                parts.append("先行有利")
            elif self.pace_bias > 0.2:
                parts.append("差し有利")
        return "・".join(parts) if parts else "顕著な傾向なし"

    def to_score(self) -> float:
        """[-2, 2] 帯域のスコアに変換。Integration 向け。"""
        raw = (self.post_bias * self.post_confidence
               + self.pace_bias * self.pace_confidence)
        return max(-2.0, min(2.0, raw * 2.0))

    def to_dict(self) -> dict[str, object]:
        """API / ログ向け辞書変換。"""
        return {
            "race_date": self.race_date.isoformat(),
            "distance": self.distance,
            "track_condition": self.track_condition.value,
            "computed_after_race": self.computed_after_race,
            "post_bias": round(self.post_bias, 3),
            "pace_bias": round(self.pace_bias, 3),
            "post_confidence": round(self.post_confidence, 3),
            "pace_confidence": round(self.pace_confidence, 3),
            "bias_strength": round(self.bias_strength, 3),
            "bias_direction": self.bias_direction,
            "sample_races": self.sample_races,
            "short_reason": self.short_reason,
            "score": round(self.to_score(), 3),
        }
