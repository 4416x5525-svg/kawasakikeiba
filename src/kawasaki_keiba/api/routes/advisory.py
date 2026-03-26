"""Advisory API: Track Bias / Historical Bias / Wind の参考情報を返す。

Gate には未接続。表示専用。
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter

from kawasaki_keiba.schemas.race import TrackCondition
from kawasaki_keiba.track_bias.snapshot import TrackBiasSnapshot
from kawasaki_keiba.wind.estimate import estimate_wind_impact

router = APIRouter(prefix="/api/advisory", tags=["advisory"])


@router.get("/track-bias")
def get_track_bias(
    race_date: str = "2026-04-01",
    distance: int = 1400,
    condition: str = "good",
) -> dict[str, object]:
    """当日 Track Bias のスナップショット（ダミー / 実データ接続後に置換）。"""
    # 実データがまだないのでデモ値を返す
    snap = TrackBiasSnapshot(
        race_date=date.fromisoformat(race_date),
        distance=distance,
        track_condition=TrackCondition(condition),
        computed_after_race=5,
        post_bias=-0.35,
        pace_bias=-0.45,
        post_confidence=0.4,
        pace_confidence=0.5,
        sample_races=5,
        short_reason="内枠有利(-0.35)・先行有利(-0.45)  [R1-R5集計/デモ]",
    )
    return {
        "module": "track_bias",
        "mode": "advisory",
        "gate_connected": False,
        "data": snap.to_dict(),
    }


@router.get("/historical-bias")
def get_historical_bias(
    distance: int = 1400,
    condition: str = "good",
    num_runners: int = 10,
) -> dict[str, object]:
    """Historical Bias のルックアップ結果（ダミー）。"""
    return {
        "module": "historical_bias",
        "mode": "advisory",
        "gate_connected": False,
        "data": {
            "distance_group": "mid" if 1000 < distance <= 1600 else ("short" if distance <= 1000 else "long"),
            "condition_group": "good" if condition in ("good", "slightly_heavy") else "heavy",
            "field_size_group": "small" if num_runners <= 6 else "normal",
            "inner_advantage": 0.05,
            "pace_advantage": 0.08,
            "significant_post": True,
            "significant_pace": True,
            "sample_races": 0,
            "confidence": 0.0,
            "short_reason": "実データ未蓄積。30レース以上で検証開始。",
            "note": "Historical Bias は Core 特徴量として使用予定。現在はデモ値。",
        },
    }


@router.get("/wind")
def get_wind(
    wind_direction: float = 180.0,
    wind_speed: float = 5.0,
    distance: int = 1400,
) -> dict[str, object]:
    """Wind 影響推定（discard 前提のスタブ）。"""
    est = estimate_wind_impact(wind_direction, wind_speed, distance)
    return {
        "module": "wind",
        "mode": "advisory",
        "gate_connected": False,
        "discard_recommended": True,
        "data": est.to_dict(),
    }


@router.get("/summary")
def advisory_summary() -> dict[str, object]:
    """3モジュールのサマリ。ダッシュボード表示用。"""
    return {
        "modules": [
            {
                "name": "Track Bias",
                "mode": "advisory",
                "status": "active",
                "gate_connected": False,
                "discard_criteria": "50開催日でバイアス方向一致率が50%以下",
                "integrated_criteria": "advisory 30開催日でROI改善 > +3%",
            },
            {
                "name": "Historical Bias",
                "mode": "advisory",
                "status": "waiting_data",
                "gate_connected": False,
                "discard_criteria": "人気補正後に edge が消失",
                "integrated_criteria": "Core F6/F7 追加でROI +2%改善",
            },
            {
                "name": "Wind",
                "mode": "advisory",
                "status": "discard_recommended",
                "gate_connected": False,
                "discard_criteria": "H1/H2 検証で p >= 0.10",
                "integrated_criteria": "到達しない想定",
            },
        ],
    }
