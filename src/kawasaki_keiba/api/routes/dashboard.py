"""ダッシュボード API — 実データ優先、なければデモ表示。"""

from __future__ import annotations

from fastapi import APIRouter

from kawasaki_keiba.api.config import DATA_PATH
from kawasaki_keiba.track_bias.compute import compute_track_bias

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

_DATA_PATH = DATA_PATH


def _load_data():
    """実データをロード。失敗したら None を返す。"""
    try:
        from kawasaki_keiba.data.loader import load_entries, load_races, load_results
        if not _DATA_PATH.exists():
            return None
        races = load_races(_DATA_PATH)
        entries = load_entries(_DATA_PATH)
        results = load_results(_DATA_PATH)
        if not races:
            return None
        return races, entries, results
    except Exception:
        return None


@router.get("/summary")
def dashboard_summary() -> dict[str, object]:
    """本日のダッシュボード概要。実データがあれば使用。"""
    loaded = _load_data()

    if loaded is None:
        return {
            "data_source": "demo",
            "today": "2026-04-01",
            "total_races": 0,
            "note": "実データファイルが見つかりません。data/raw/sample_races.json を配置してください。",
        }

    races, entries, results = loaded

    # Track Bias 算出
    snap = compute_track_bias(races, entries, results)

    # 基本集計
    total_horses = sum(len(v) for v in entries.values())
    distances = sorted({r.distance for r in races})
    conditions = sorted({r.track_condition.value for r in races})

    # 各レースの1番人気勝率（baseline ROI の簡易指標）
    fav_wins = 0
    total_with_results = 0
    for race in races:
        r_entries = entries.get(race.race_id, [])
        r_results = results.get(race.race_id, [])
        if not r_entries or not r_results:
            continue
        fav = next((e for e in r_entries if e.popularity == 1), None)
        if fav is None:
            continue
        fav_result = next((r for r in r_results if r.horse_number == fav.horse_number), None)
        if fav_result is None:
            continue
        total_with_results += 1
        if fav_result.finish_position == 1:
            fav_wins += 1

    fav_win_rate = fav_wins / total_with_results if total_with_results else 0.0

    return {
        "data_source": "real",
        "today": races[0].race_date.isoformat(),
        "total_races": len(races),
        "total_horses": total_horses,
        "distances": distances,
        "conditions": conditions,
        "predicted": len(races),
        "unpredicted": 0,
        "bet_count": 0,
        "no_bet_count": len(races),
        "danger_popular_count": 0,
        "baseline_fav_win_rate": round(fav_win_rate, 3),
        "system_status": {
            "alert_level": "NORMAL",
            "halt_active": False,
            "data_status": f"{len(races)}R 蓄積済み（M1まであと{max(0, 30 - len(races))}R）",
        },
        "subsystem_modes": {
            "core": "active",
            "gate": "active",
            "race_video": "advisory",
            "paddock": "advisory",
            "warmup": "off",
            "track_bias": "advisory",
            "historical_bias": "waiting_data",
            "wind": "discard_recommended",
        },
        "advisory_modules": {
            "track_bias": {
                "score": snap.to_score(),
                "score_available": snap.sample_races >= 3,
                "confidence": snap.pace_confidence,
                "short_reason": snap.short_reason,
                "direction": snap.bias_direction,
                "affects_gate": False,
            },
            "historical_bias": {
                "score": None,
                "score_available": False,
                "confidence": 0.0,
                "short_reason": f"M0: {len(races)}R蓄積（M1開始まであと{max(0, 30 - len(races))}R）",
                "affects_gate": False,
                "milestone": "M0",
            },
            "wind": {
                "score": None,
                "score_available": False,
                "confidence": 0.05,
                "short_reason": "discard推奨。500R蓄積後に検証予定。",
                "affects_gate": False,
            },
        },
        "advisory_note": "advisory_modules は参考情報。Gate・投資判定には使いません。",
    }
