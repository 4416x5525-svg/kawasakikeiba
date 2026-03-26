"""Core scoring: 市場確率を出発点とし、logit 空間で補正を加える。

Phase 2: adjustment = 0（市場通り）。edge = 0。全レース no-bet。
Phase 3: features.py から特徴量 F1-F7 を受け取り、adjustment > 0 で edge を生成。

baseline.py との違い:
  - baseline は「比較基準」（これを上回れなければ Core は不要）
  - scoring は「実際の予測器」（市場確率 + 補正 = Core の予測）
"""

from __future__ import annotations

import math

from kawasaki_keiba.core.market import market_probs_from_odds, normalize_probs
from kawasaki_keiba.schemas.prediction import CorePrediction
from kawasaki_keiba.schemas.race import HorseEntry

# logit 補正の最大幅（暴走防止）
MAX_LOGIT_ADJUSTMENT = 1.0

# UNVALIDATED: 初期重み（実データ検証後に調整）
INITIAL_WEIGHTS: dict[str, float] = {
    "distance_fit": 0.4,
    "condition_fit": 0.3,
    "form_trend": 0.5,
    "class_delta": 0.3,
    "jockey_venue_edge": 0.2,
    "post_advantage": 0.15,
    "pace_advantage": 0.15,
}


def market_adjusted_prob(market_prob: float, adjustment: float) -> float:
    """市場確率に logit 空間で補正を加える。

    Args:
        market_prob: 市場推定勝率 (0, 1)
        adjustment: logit 空間での補正量。正=勝率上方修正、負=下方修正。

    Returns:
        補正後の確率 (0, 1)
    """
    if market_prob <= 0.001:
        return 0.001
    if market_prob >= 0.999:
        return 0.999
    logit = math.log(market_prob / (1.0 - market_prob))
    clamped = max(-MAX_LOGIT_ADJUSTMENT, min(MAX_LOGIT_ADJUSTMENT, adjustment))
    return 1.0 / (1.0 + math.exp(-(logit + clamped)))


def compute_adjustment(features: dict[str, float] | None = None) -> float:
    """特徴量から logit 補正量を算出する。

    Phase 2: features=None → adjustment=0（市場通り）。
    Phase 3: features={F1..F7} → weighted sum → adjustment。
    """
    if not features:
        return 0.0
    total = sum(
        INITIAL_WEIGHTS.get(k, 0.0) * v
        for k, v in features.items()
    )
    return max(-MAX_LOGIT_ADJUSTMENT, min(MAX_LOGIT_ADJUSTMENT, total))


def generate_core_predictions(
    entries: list[HorseEntry],
    features_by_horse: dict[int, dict[str, float]] | None = None,
) -> list[CorePrediction]:
    """Core の予測を生成する。

    Args:
        entries: 出走馬リスト（odds_win が必要）
        features_by_horse: {horse_number: {feature_name: value}}
            None なら全馬 adjustment=0（市場確率をそのまま返す）

    Returns:
        CorePrediction リスト。edge_win = core_prob - market_prob。
    """
    num_runners = len(entries)
    if num_runners == 0:
        return []

    # 市場確率を算出
    odds = [e.odds_win for e in entries if e.odds_win is not None and e.odds_win > 0]
    if len(odds) < 2:
        # オッズ不足 → 均等確率で代替（edge=0）
        uniform = 1.0 / num_runners
        return [
            CorePrediction(
                race_id=entry.race_id,
                horse_id=entry.horse_id,
                horse_number=entry.horse_number,
                rank_score=0.5,
                win_prob=uniform,
                place_prob=min(1.0, uniform * num_runners / 3),
                market_win_prob=uniform,
                edge_win=0.0,
                edge_place=0.0,
            )
            for entry in entries
        ]

    # odds が全馬分ある前提で市場確率を算出
    entries_with_odds = [e for e in entries if e.odds_win is not None and e.odds_win > 0]
    mkt_probs = market_probs_from_odds([e.odds_win for e in entries_with_odds])
    mkt_map = {e.horse_number: p for e, p in zip(entries_with_odds, mkt_probs)}

    # 特徴量ベースの補正
    raw_core_probs: dict[int, float] = {}
    for entry in entries:
        mkt_p = mkt_map.get(entry.horse_number, 1.0 / num_runners)
        features = (features_by_horse or {}).get(entry.horse_number)
        adj = compute_adjustment(features)
        raw_core_probs[entry.horse_number] = market_adjusted_prob(mkt_p, adj)

    # レース内正規化（合計 = 1.0）
    total = sum(raw_core_probs.values())
    if total <= 0:
        total = 1.0
    core_probs = {hn: p / total for hn, p in raw_core_probs.items()}

    # CorePrediction 生成
    # rank_score: core_prob 降順で 1.0 → 0.0
    sorted_by_prob = sorted(core_probs.items(), key=lambda x: x[1], reverse=True)
    rank_map = {hn: 1.0 - i / max(len(sorted_by_prob) - 1, 1) for i, (hn, _) in enumerate(sorted_by_prob)}

    predictions: list[CorePrediction] = []
    for entry in entries:
        hn = entry.horse_number
        core_p = core_probs.get(hn, 1.0 / num_runners)
        mkt_p = mkt_map.get(hn, 1.0 / num_runners)
        place_p = min(1.0, core_p * num_runners / 3)
        predictions.append(
            CorePrediction(
                race_id=entry.race_id,
                horse_id=entry.horse_id,
                horse_number=hn,
                rank_score=rank_map.get(hn, 0.5),
                win_prob=core_p,
                place_prob=place_p,
                market_win_prob=mkt_p,
                edge_win=core_p - mkt_p,
                edge_place=place_p - mkt_p,
            ),
        )
    return predictions
