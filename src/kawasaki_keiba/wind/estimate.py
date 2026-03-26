"""Wind 影響推定の最小実装。

川崎競馬場の直線方向は概ね南北。
北風 = 直線追い風（差し有利仮説）
南風 = 直線向かい風（先行有利仮説）

confidence は常に低値。discard 前提で設計。
"""

from __future__ import annotations

import math
from dataclasses import dataclass


# 川崎競馬場の直線方向（ゴール方向の角度、北=0度、時計回り）
# 4コーナー → ゴール: 概ね北北東方向（約20度）
KAWASAKI_STRAIGHT_BEARING_DEG = 20.0

# confidence の上限（Wind モジュール全体で低く抑える）
MAX_WIND_CONFIDENCE = 0.3


@dataclass(frozen=True)
class WindEstimate:
    """風の影響推定結果。

    Attributes:
        wind_direction_deg: 風向き（度、北=0、時計回り）
        wind_speed_mps: 風速（m/s）
        headwind_component: 直線向かい風成分（m/s, 正=向かい風）
        tailwind_component: 直線追い風成分（m/s, 正=追い風）
        impact_hypothesis: 影響仮説の1行説明
        wind_score: [-2, 2] スコア（先行有利方向が負、差し有利方向が正）
        confidence: 信頼度 [0, MAX_WIND_CONFIDENCE]
        short_reason: 人間向け説明
    """

    wind_direction_deg: float
    wind_speed_mps: float
    headwind_component: float
    tailwind_component: float
    impact_hypothesis: str
    wind_score: float
    confidence: float
    short_reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "wind_direction_deg": self.wind_direction_deg,
            "wind_speed_mps": self.wind_speed_mps,
            "headwind_component": round(self.headwind_component, 2),
            "tailwind_component": round(self.tailwind_component, 2),
            "impact_hypothesis": self.impact_hypothesis,
            "wind_score": round(self.wind_score, 3),
            "confidence": round(self.confidence, 3),
            "short_reason": self.short_reason,
        }


def _wind_direction_to_str(deg: float) -> str:
    """角度を16方位文字列に変換。"""
    directions = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
    ]
    idx = round(deg / 22.5) % 16
    return directions[idx]


def estimate_wind_impact(
    wind_direction_deg: float,
    wind_speed_mps: float,
    distance: int = 1400,
) -> WindEstimate:
    """風向き・風速から直線方向の影響を推定する。

    Args:
        wind_direction_deg: 風向き（度、北=0、風が吹いてくる方向）
        wind_speed_mps: 風速（m/s）
        distance: レース距離（m）。短距離ほど直線の比率が高い。
    """
    if wind_speed_mps < 0:
        wind_speed_mps = 0.0

    # 風が吹いてくる方向 → 風のベクトル方向（180度反転）
    wind_vector_deg = (wind_direction_deg + 180) % 360

    # 直線方向との角度差
    angle_diff = math.radians(wind_vector_deg - KAWASAKI_STRAIGHT_BEARING_DEG)

    # 直線方向の風成分（正 = 追い風）
    tailwind = wind_speed_mps * math.cos(angle_diff)
    headwind = -tailwind

    # スコア算出
    # 追い風 → 差し有利仮説 → 正のスコア
    # 向かい風 → 先行有利仮説 → 負のスコア
    # ただし影響は小さいので scaling を抑える
    raw_score = tailwind * 0.1  # 10m/s追い風で+1.0程度

    # distance による補正（短距離ほど直線の比率が高い）
    if distance <= 1000:
        distance_factor = 1.2
    elif distance <= 1600:
        distance_factor = 1.0
    else:
        distance_factor = 0.7

    score = max(-2.0, min(2.0, raw_score * distance_factor))

    # confidence は常に低い
    if wind_speed_mps < 3:
        conf = 0.05  # 微風は影響なし
    elif wind_speed_mps < 7:
        conf = 0.15
    else:
        conf = MAX_WIND_CONFIDENCE  # 最大でも 0.3

    # 仮説
    wind_dir_str = _wind_direction_to_str(wind_direction_deg)
    if abs(tailwind) < 1.0:
        hypothesis = "横風中心。直線への影響は限定的"
        reason = f"{wind_dir_str} {wind_speed_mps:.0f}m/s: 直線への影響小"
    elif tailwind > 0:
        hypothesis = f"直線追い風{tailwind:.1f}m/s。差し馬にやや有利の仮説"
        reason = f"{wind_dir_str} {wind_speed_mps:.0f}m/s: 直線追い風→差し有利?"
    else:
        hypothesis = f"直線向かい風{headwind:.1f}m/s。先行馬にやや有利の仮説"
        reason = f"{wind_dir_str} {wind_speed_mps:.0f}m/s: 直線向かい風→先行有利?"

    return WindEstimate(
        wind_direction_deg=wind_direction_deg,
        wind_speed_mps=wind_speed_mps,
        headwind_component=round(headwind, 2),
        tailwind_component=round(tailwind, 2),
        impact_hypothesis=hypothesis,
        wind_score=round(score, 3),
        confidence=round(conf, 3),
        short_reason=reason,
    )
