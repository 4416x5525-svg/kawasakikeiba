"""Gate 判定のエントリポイント。

CorePrediction[] + RaceRecord → GateDecision を生成する。
内部で integration 経由で rules.evaluate_gate_minimal を呼ぶ。
映像系スコアが未入力でも動作する。
"""

from __future__ import annotations

from datetime import datetime

from kawasaki_keiba.gate.reason_codes import NoBetReasonCode
from kawasaki_keiba.gate.rules import GateRuleInput, GateRuleResult, evaluate_gate_minimal
from kawasaki_keiba.integration.score_normalization import rescale_to_band
from kawasaki_keiba.schemas.prediction import (
    BetReason,
    CorePrediction,
    GateDecision,
    NoBetReason,
)
from kawasaki_keiba.schemas.race import RaceRecord

# edge → 正規化バンド [-2, 2] のソースレンジ
# 川崎競馬で edge ±10% は十分に大きい
DEFAULT_EDGE_SRC = (-0.10, 0.10)

# レースレベルの no-bet 条件
SMALL_FIELD_THRESHOLD = 4
MIN_HORSES_WITH_ODDS = 3


def aggregate_core_score(
    predictions: list[CorePrediction],
    *,
    edge_src: tuple[float, float] = DEFAULT_EDGE_SRC,
) -> float | None:
    """CorePrediction リストからレースレベルの core スコアを算出する。

    max(edge_win) を [-2, 2] バンドに正規化して返す。
    """
    if not predictions:
        return None
    max_edge = max(p.edge_win for p in predictions)
    return rescale_to_band(max_edge, src_low=edge_src[0], src_high=edge_src[1])


def check_race_conditions(
    predictions: list[CorePrediction],
    race: RaceRecord,
) -> list[NoBetReason]:
    """レースレベルの no-bet 条件をチェックする。

    Gate ルール評価の前段で、レース自体の問題を検出する。
    """
    reasons: list[NoBetReason] = []

    if race.num_runners <= SMALL_FIELD_THRESHOLD:
        reasons.append(NoBetReason.SMALL_FIELD)

    horses_with_odds = sum(1 for p in predictions if p.market_win_prob > 0)
    if horses_with_odds < MIN_HORSES_WITH_ODDS:
        reasons.append(NoBetReason.INSUFFICIENT_DATA)

    return reasons


def _map_gate_result_to_decision(
    race_id: str,
    result: GateRuleResult,
    pre_reasons: list[NoBetReason],
) -> GateDecision:
    """GateRuleResult + レースレベル理由 → schemas.GateDecision に変換する。"""
    # レースレベルの理由がある場合は強制 no-bet
    if pre_reasons:
        return GateDecision(
            race_id=race_id,
            decision="no_bet",
            no_bet_reasons=pre_reasons,
            confidence=0.9,
            timestamp=datetime.now(),
        )

    # ルールベースの結果をマッピング
    no_bet_reasons = _map_no_bet_codes(result.no_bet_reasons)
    bet_reasons = _map_bet_codes(result.bet_reasons)

    return GateDecision(
        race_id=race_id,
        decision="bet" if result.bet else "no_bet",
        no_bet_reasons=no_bet_reasons,
        bet_reasons=bet_reasons,
        confidence=0.5 if result.bet else 0.7,
        timestamp=datetime.now(),
    )


def run_gate(
    predictions: list[CorePrediction],
    race: RaceRecord,
    *,
    race_score: float | None = None,
    paddock_score: float | None = None,
    warmup_score: float | None = None,
    race_video_veto: bool = False,
    paddock_veto: bool = False,
    warmup_veto: bool = False,
) -> GateDecision:
    """Gate 判定のメインエントリポイント。

    Args:
        predictions: Core モデルの予測出力
        race: レース基本情報
        race_score: レース映像スコア（未入力可, [-2,2] 正規化済み想定）
        paddock_score: パドックスコア（未入力可）
        warmup_score: 返し馬スコア（未入力可）
        race_video_veto: レース映像拒否権フラグ
        paddock_veto: パドック拒否権フラグ
        warmup_veto: 返し馬拒否権フラグ

    Returns:
        GateDecision (schemas 層)

    Note:
        映像系スコア/拒否権が未設定の場合は Core のみで判定する。
        TODO: Phase 3-4 で video/paddock/warmup の自動入力を接続する。
    """
    # 1. レースレベル条件チェック
    pre_reasons = check_race_conditions(predictions, race)
    if pre_reasons:
        return _map_gate_result_to_decision(
            race.race_id,
            GateRuleResult(bet=False),
            pre_reasons,
        )

    # 2. Core スコア算出
    core_score = aggregate_core_score(predictions)

    # 3. Gate ルール評価
    gate_input = GateRuleInput(
        core=core_score,
        race=race_score,
        paddock=paddock_score,
        warmup=warmup_score,
        race_video_veto=race_video_veto,
        paddock_veto=paddock_veto,
        warmup_veto=warmup_veto,
        require_core=True,
    )
    result = evaluate_gate_minimal(gate_input)

    return _map_gate_result_to_decision(race.race_id, result, [])


# ---------------------------------------------------------------------------
# 理由コードのマッピング: gate.reason_codes ↔ schemas.prediction
# ---------------------------------------------------------------------------

_NO_BET_CODE_MAP: dict[NoBetReasonCode, NoBetReason] = {
    NoBetReasonCode.WEAK_CORE: NoBetReason.NO_EDGE,
    NoBetReasonCode.WEAK_AGGREGATE: NoBetReason.LOW_CONFIDENCE,
    NoBetReasonCode.INSUFFICIENT_SIGNAL: NoBetReason.INSUFFICIENT_DATA,
    NoBetReasonCode.MISSING_REQUIRED_SCORE: NoBetReason.INSUFFICIENT_DATA,
    NoBetReasonCode.VIDEO_VETO: NoBetReason.VIDEO_VETO,
    NoBetReasonCode.PADDOCK_VETO: NoBetReason.PADDOCK_ALERT,
    NoBetReasonCode.WARMUP_VETO: NoBetReason.WARMUP_ALERT,
    NoBetReasonCode.MONITORING_HALT: NoBetReason.MONITORING_HALT,
}

_BET_CODE_MAP: dict[str, BetReason] = {
    "rule_pass": BetReason.POSITIVE_EDGE,
    "core_support": BetReason.POSITIVE_EDGE,
    "consensus_support": BetReason.CONDITION_PLUS,
}


def _map_no_bet_codes(codes: tuple[NoBetReasonCode, ...]) -> list[NoBetReason]:
    return [_NO_BET_CODE_MAP.get(c, NoBetReason.LOW_CONFIDENCE) for c in codes]


def _map_bet_codes(codes: tuple[str, ...]) -> list[BetReason]:
    seen: set[BetReason] = set()
    result: list[BetReason] = []
    for c in codes:
        mapped = _BET_CODE_MAP.get(str(c), BetReason.POSITIVE_EDGE)
        if mapped not in seen:
            seen.add(mapped)
            result.append(mapped)
    return result
