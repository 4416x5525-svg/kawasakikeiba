"""統合判定の雛形: 正規化 →（映像系拒否権は TODO）→ Gate 最小ルール。"""

from __future__ import annotations

from dataclasses import dataclass

from kawasaki_ai.gate.rules import GateRuleInput, GateRuleResult, evaluate_gate_minimal
from kawasaki_ai.integration.score_normalization import (
    normalize_core_score,
    normalize_paddock_score,
    normalize_race_score,
    normalize_warmup_score,
)


@dataclass(frozen=True)
class RawSubsystemScores:
    """各サブシステムの生スコア（正規化前）。未使用は None。"""

    core: float | None = None
    race: float | None = None
    paddock: float | None = None
    warmup: float | None = None


@dataclass(frozen=True)
class IntegrationDecision:
    """統合結果（雛形）。"""

    normalized: dict[str, float]
    race_video_veto: bool
    paddock_veto: bool
    warmup_veto: bool
    gate: GateRuleResult


def resolve_video_veto_flags(
    *,
    raw: RawSubsystemScores,
    race_tags: object | None = None,
    paddock_observation: object | None = None,
    warmup_observation: object | None = None,
) -> tuple[bool, bool, bool]:
    """映像系拒否権フラグ（現状は常に False）。

    TODO（条件は後続で実装・ここに集約する想定）:
    - レース映像（race_video）拒否権:
        - 観測タグ／コメントに基づく「買い不可」パターン（例: 明確な不利確定・再現性ある拒否ルール）
        - Core とは独立した hard veto のみ（主観断定・未来情報は禁止）
    - パドック拒否権:
        - paddock の danger / alert 相当の閾値超過、または観測上の hard negative
    - 返し馬（warmup）拒否権:
        - anomaly / alert 相当の閾値超過、または直前異常の hard negative

    上記は `race_tags` / `paddock_observation` / `warmup_observation` を入力に評価し、
    True のとき `GateRuleInput` の `*_veto` に反映する。
    """
    _ = raw
    _ = race_tags
    _ = paddock_observation
    _ = warmup_observation
    return (False, False, False)


def build_integration_decision(
    raw: RawSubsystemScores,
    *,
    require_core: bool = True,
    core_src: tuple[float, float] = (-1.0, 1.0),
    race_src: tuple[float, float] = (-1.0, 1.0),
    paddock_src: tuple[float, float] = (-1.0, 1.0),
    warmup_src: tuple[float, float] = (-1.0, 1.0),
) -> IntegrationDecision:
    """生スコアを [-2,2] に揃え、拒否権 TODO を経由して Gate を評価する。"""
    norm: dict[str, float] = {}
    if raw.core is not None:
        norm["core"] = normalize_core_score(
            raw.core, src_low=core_src[0], src_high=core_src[1]
        )
    if raw.race is not None:
        norm["race"] = normalize_race_score(
            raw.race, src_low=race_src[0], src_high=race_src[1]
        )
    if raw.paddock is not None:
        norm["paddock"] = normalize_paddock_score(
            raw.paddock, src_low=paddock_src[0], src_high=paddock_src[1]
        )
    if raw.warmup is not None:
        norm["warmup"] = normalize_warmup_score(
            raw.warmup, src_low=warmup_src[0], src_high=warmup_src[1]
        )

    rv, pv, wv = resolve_video_veto_flags(raw=raw)

    gate_in = GateRuleInput(
        core=norm.get("core"),
        race=norm.get("race"),
        paddock=norm.get("paddock"),
        warmup=norm.get("warmup"),
        race_video_veto=rv,
        paddock_veto=pv,
        warmup_veto=wv,
        require_core=require_core,
    )
    return IntegrationDecision(
        normalized=dict(norm),
        race_video_veto=rv,
        paddock_veto=pv,
        warmup_veto=wv,
        gate=evaluate_gate_minimal(gate_in),
    )


__all__ = [
    "IntegrationDecision",
    "RawSubsystemScores",
    "build_integration_decision",
    "resolve_video_veto_flags",
]
