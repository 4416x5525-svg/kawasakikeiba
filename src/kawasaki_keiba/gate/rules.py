"""Gate 最小ルール（閾値ベース、ML なし）。"""

from __future__ import annotations

from dataclasses import dataclass

from kawasaki_keiba.gate.reason_codes import BetReasonCode, NoBetReasonCode

# 最小ルール用の既定閾値（後続で設定化してよい）
CORE_NO_BET_BELOW: float = -1.0
AGGREGATE_NO_BET_BELOW: float = -0.5


@dataclass(frozen=True)
class GateRuleInput:
    """正規化済みスコア（[-2, 2]）と映像系拒否フラグ。"""

    core: float | None
    race: float | None = None
    paddock: float | None = None
    warmup: float | None = None
    race_video_veto: bool = False
    paddock_veto: bool = False
    warmup_veto: bool = False
    require_core: bool = True


@dataclass(frozen=True)
class GateRuleResult:
    """判定と理由コード列。"""

    bet: bool
    no_bet_reasons: tuple[NoBetReasonCode, ...] = ()
    bet_reasons: tuple[BetReasonCode, ...] = ()


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _collect_parts(inp: GateRuleInput) -> list[float] | None:
    parts: list[float] = []
    if inp.core is not None:
        parts.append(inp.core)
    for x in (inp.race, inp.paddock, inp.warmup):
        if x is not None:
            parts.append(x)
    if not parts:
        return None
    return parts


def evaluate_gate_minimal(inp: GateRuleInput) -> GateRuleResult:
    """最小 Gate: 拒否権 → 必須 Core 欠損 → Core 弱体 → 平均弱体 → それ以外は bet。

    映像系拒否権（フラグの意味・条件名の予定）:
    - race_video_veto … RACE_VIDEO_HARD_TAG_VETO, RACE_VIDEO_RECURRENCE_HIGH_VETO
    - paddock_veto … PADDOCK_DANGER_SCORE_OVER_THRESHOLD, PADDOCK_ALERT_FLAG_SET
    - warmup_veto … WARMUP_ANOMALY_SCORE_OVER_THRESHOLD, WARMUP_ALERT_FLAG_SET

    上記条件の評価は integration.decision.resolve_video_veto_flags に集約する（現状は未実装）。
    """
    nb: list[NoBetReasonCode] = []
    br: list[BetReasonCode] = []

    if inp.race_video_veto:
        nb.append(NoBetReasonCode.VIDEO_VETO)
    if inp.paddock_veto:
        nb.append(NoBetReasonCode.PADDOCK_VETO)
    if inp.warmup_veto:
        nb.append(NoBetReasonCode.WARMUP_VETO)
    if nb:
        return GateRuleResult(bet=False, no_bet_reasons=tuple(nb))

    if inp.require_core and inp.core is None:
        return GateRuleResult(
            bet=False,
            no_bet_reasons=(NoBetReasonCode.MISSING_REQUIRED_SCORE,),
        )

    parts = _collect_parts(inp)
    if parts is None:
        return GateRuleResult(
            bet=False,
            no_bet_reasons=(NoBetReasonCode.INSUFFICIENT_SIGNAL,),
        )

    if inp.core is not None and inp.core < CORE_NO_BET_BELOW:
        nb.append(NoBetReasonCode.WEAK_CORE)

    agg = _mean(parts)
    if agg < AGGREGATE_NO_BET_BELOW:
        nb.append(NoBetReasonCode.WEAK_AGGREGATE)

    if nb:
        return GateRuleResult(bet=False, no_bet_reasons=tuple(dict.fromkeys(nb)))

    br.append(BetReasonCode.RULE_PASS)
    if inp.core is not None and inp.core >= 0.0:
        br.append(BetReasonCode.CORE_SUPPORT)
    if (
        inp.race is not None
        and inp.paddock is not None
        and inp.warmup is not None
        and all(x >= 0.0 for x in (inp.race, inp.paddock, inp.warmup))
    ):
        br.append(BetReasonCode.CONSENSUS_SUPPORT)

    return GateRuleResult(bet=True, bet_reasons=tuple(dict.fromkeys(br)))
