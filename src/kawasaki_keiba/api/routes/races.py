"""レース一覧・詳細 API。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from kawasaki_keiba.data.loader import (
    load_entries,
    load_races,
    load_results,
    validate_race_bundle,
)
from kawasaki_keiba.schemas.race import HorseEntry, RaceRecord, RaceResult

router = APIRouter(prefix="/api/races", tags=["races"])

_DUMMY_LIST: dict[str, object] = {
    "date": "2026-04-01",
    "races": [
        {
            "race_id": "20260401_KW_01",
            "race_number": 1,
            "distance": 900,
            "grade": "C3",
            "condition": "good",
            "num_runners": 10,
            "gate_decision": "no_bet",
            "no_bet_reasons": ["no_edge"],
            "short_reason": "edge不足",
        },
        {
            "race_id": "20260401_KW_05",
            "race_number": 5,
            "distance": 1400,
            "grade": "B2",
            "condition": "good",
            "num_runners": 12,
            "gate_decision": "bet",
            "bet_reasons": ["positive_edge"],
            "bet_target": [3],
            "short_reason": "#3 edge+0.04",
        },
        {
            "race_id": "20260401_KW_07",
            "race_number": 7,
            "distance": 1500,
            "grade": "B1",
            "condition": "good",
            "num_runners": 11,
            "gate_decision": "no_bet",
            "no_bet_reasons": ["paddock_alert"],
            "short_reason": "PADDOCK_ALERT: #2 状態BAD",
        },
        {
            "race_id": "20260401_KW_09",
            "race_number": 9,
            "distance": 1600,
            "grade": "A2",
            "condition": "slightly_heavy",
            "num_runners": 14,
            "gate_decision": "no_bet",
            "no_bet_reasons": ["small_field"],
            "short_reason": "少頭数",
        },
    ],
    "note": "デモデータ",
}


def _dummy_detail(race_id: str) -> dict[str, object]:
    return {
        "race_id": race_id,
        "race_number": 7,
        "distance": 1500,
        "grade": "B1",
        "condition": "good",
        "num_runners": 11,
        "decision": {
            "gate_decision": "no_bet",
            "no_bet_reasons": ["paddock_alert"],
            "decisive_factor": "PADDOCK_ALERT: bet候補 #2 のパドック状態が BAD",
            "counterfactual": "Paddock vetoがなければ bet 判定だった（Core edge=+0.038）",
        },
        "horses": [
            {
                "number": 1,
                "name": "ホースA",
                "popularity": 3,
                "odds": 5.2,
                "core_edge": 0.02,
                "paddock": "G",
                "warmup": "G",
                "status": "-",
            },
            {
                "number": 2,
                "name": "ホースB",
                "popularity": 1,
                "odds": 2.5,
                "core_edge": 0.038,
                "paddock": "B",
                "warmup": "G",
                "status": "VETO",
            },
            {
                "number": 3,
                "name": "ホースC",
                "popularity": 2,
                "odds": 3.8,
                "core_edge": 0.01,
                "paddock": "G",
                "warmup": "G",
                "status": "-",
            },
            {
                "number": 4,
                "name": "ホースD",
                "popularity": 5,
                "odds": 12.0,
                "core_edge": -0.02,
                "paddock": "N",
                "warmup": "G",
                "status": "-",
            },
            {
                "number": 5,
                "name": "ホースE",
                "popularity": 4,
                "odds": 8.0,
                "core_edge": 0.03,
                "paddock": "G",
                "warmup": "G",
                "status": "候補",
            },
        ],
        "advisory": {
            "track_bias": {
                "score": -0.8,
                "score_available": True,
                "confidence": 0.4,
                "short_reason": "当日トラック: 内枠・先行がやや有利（参考）",
                "affects_gate": False,
                "post_bias": -0.35,
                "pace_bias": -0.45,
                "direction": "内枠有利・先行有利",
            },
            "wind": {
                "score": -0.15,
                "score_available": True,
                "confidence": 0.15,
                "short_reason": "風: 直線追い風寄り（参考・低信頼）",
                "affects_gate": False,
                "wind_score": -0.15,
            },
            "historical_bias": {
                "score": None,
                "score_available": False,
                "confidence": 0.0,
                "short_reason": (
                    "履歴バイアス: まだスコアなし（M0 蓄積中）。"
                    "30 レースで M1、以降 M2/M3 で検証。"
                ),
                "affects_gate": False,
                "milestone": "M0",
            },
        },
        "advisory_note": "上記3モジュールは Gate 判定に使用していません（参考表示のみ）。",
        "note": "デモデータ",
    }


def _sample_json_path() -> Path:
    from kawasaki_keiba.api.config import DATA_PATH
    return DATA_PATH


def _load_sample_bundle() -> (
    tuple[list[RaceRecord], dict[str, list[HorseEntry]], dict[str, list[RaceResult]], list[str]]
    | None
):
    path = _sample_json_path()
    if not path.is_file():
        return None
    try:
        races = load_races(path)
        entries = load_entries(path)
        results = load_results(path)
        if not races:
            return None
        warns = validate_race_bundle(races, entries, results)
        return races, entries, results, warns
    except (OSError, ValueError, TypeError):
        return None


def _detail_from_sample(
    race: RaceRecord,
    ent: list[HorseEntry],
    res_list: list[RaceResult],
    warns: list[str],
) -> dict[str, object]:
    from kawasaki_keiba.core.scoring import generate_core_predictions

    res_by_num = {x.horse_number: x for x in res_list}

    # Core scoring（adj=0 → edge≈0、将来特徴量追加で改善）
    try:
        preds = generate_core_predictions(ent)
        pred_by_num = {p.horse_number: p for p in preds}
    except Exception:
        pred_by_num = {}

    horses: list[dict[str, object]] = []
    for e in sorted(ent, key=lambda x: x.horse_number):
        rr = res_by_num.get(e.horse_number)
        pred = pred_by_num.get(e.horse_number)
        horses.append(
            {
                "number": e.horse_number,
                "name": e.horse_name,
                "popularity": e.popularity,
                "odds": e.odds_win,
                "finish_position": rr.finish_position if rr else None,
                "finish_time": rr.finish_time if rr else None,
                "last_3f": rr.last_3f if rr else None,
                "corner_positions": rr.corner_positions if rr else None,
                "core_edge": round(pred.edge_win, 4) if pred else None,
                "win_prob": round(pred.win_prob, 4) if pred else None,
                "market_prob": round(pred.market_win_prob, 4) if pred else None,
                "paddock": "-",
                "warmup": "-",
                "status": "-",
            },
        )
    return {
        "race_id": race.race_id,
        "race_number": race.race_number,
        "distance": race.distance,
        "grade": str(race.grade),
        "condition": str(race.track_condition),
        "num_runners": race.num_runners,
        "decision": {
            "gate_decision": "no_bet",
            "no_bet_reasons": ["sample_data"],
            "decisive_factor": "実データ読込のみ（ゲート未計算）",
            "counterfactual": "-",
        },
        "horses": horses,
        "advisory": {
            "track_bias": {
                "score": None,
                "score_available": False,
                "confidence": 0.0,
                "short_reason": "（参考）sample データ — スコアなし",
                "affects_gate": False,
                "post_bias": None,
                "pace_bias": None,
                "direction": None,
            },
            "wind": {
                "score": None,
                "score_available": False,
                "confidence": 0.0,
                "short_reason": "（参考）sample データ — スコアなし",
                "affects_gate": False,
                "wind_score": None,
            },
            "historical_bias": {
                "score": None,
                "score_available": False,
                "confidence": 0.0,
                "short_reason": "（参考）sample データ — スコアなし",
                "affects_gate": False,
                "milestone": "M0",
            },
        },
        "advisory_note": "上記3モジュールは Gate 判定に使用していません（参考表示のみ）。",
        "note": "sample_races.json",
        "load_warnings": warns,
    }


@router.get("/")
def list_races() -> dict[str, object]:
    """本日のレース一覧。"""
    loaded = _load_sample_bundle()
    if loaded is None:
        return _DUMMY_LIST
    races, _entries, _results, warns = loaded
    d0 = min(r.race_date for r in races)
    return {
        "date": d0.isoformat(),
        "total": len(races),
        "races": [
            {
                "race_id": r.race_id,
                "race_date": r.race_date.isoformat(),
                "race_number": r.race_number,
                "distance": r.distance,
                "grade": str(r.grade),
                "condition": str(r.track_condition),
                "num_runners": r.num_runners,
                "gate_decision": "no_bet",
                "no_bet_reasons": ["sample_data"],
                "short_reason": f"{r.distance}m {r.grade} {r.num_runners}頭",
            }
            for r in sorted(races, key=lambda x: (x.race_date, x.race_number))
        ],
    }


@router.get("/{race_id}")
def get_race(race_id: str) -> dict[str, object]:
    """レース詳細。"""
    loaded = _load_sample_bundle()
    if loaded is None:
        return _dummy_detail(race_id)
    races, entries, results, warns = loaded
    race = next((r for r in races if r.race_id == race_id), None)
    if race is None:
        raise HTTPException(status_code=404, detail="race not found in sample_races.json")
    ent = entries.get(race_id, [])
    res_list = results.get(race_id, [])
    return _detail_from_sample(race, ent, res_list, warns)
