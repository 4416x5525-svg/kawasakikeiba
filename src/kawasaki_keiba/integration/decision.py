"""統合判定: 安全正規化 → 映像系拒否権(TODO) → Gate 最小ルール。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from kawasaki_keiba.gate.rules import GateRuleInput, GateRuleResult, evaluate_gate_minimal
from kawasaki_keiba.integration.score_normalization import (
    safe_normalize_core_score,
    safe_normalize_paddock_score,
    safe_normalize_race_score,
    safe_normalize_warmup_score,
    safe_rescale_to_band,
)


class IntegrationMode(StrEnum):
    """統合レイヤーと Gate の接続モード。

    INTEGRATED … 全サブシステムを Gate 集約に渡す。
    ADVISORY … normalized には全サブシステムを載せつつ、Gate には Core のみ渡す。
    """

    INTEGRATED = "integrated"
    ADVISORY = "advisory"


@dataclass(frozen=True)
class RawSubsystemScores:
    """各サブシステムの生スコア（正規化前）。未使用・非有限は None 扱いにできる。

    track_bias_score / wind_score / historical_bias_score は Track Bias・風・履歴バイアス
    モジュール接続用（現状は正規化のみ Gate 外に保持）。
    """

    core: float | None = None
    race: float | None = None
    paddock: float | None = None
    warmup: float | None = None
    track_bias_score: float | None = None
    wind_score: float | None = None
    historical_bias_score: float | None = None


@dataclass(frozen=True)
class IntegrationDecision:
    """統合結果。explain は説明可能性用の不変トレース (key, value) 列。"""

    mode: IntegrationMode
    normalized: dict[str, float]
    race_video_veto: bool
    paddock_veto: bool
    warmup_veto: bool
    gate: GateRuleResult
    explain: tuple[tuple[str, str], ...] = ()


def resolve_video_veto_flags(
    *,
    raw: RawSubsystemScores,
    race_tags: object | None = None,
    paddock_observation: object | None = None,
    warmup_observation: object | None = None,
) -> tuple[bool, bool, bool]:
    """映像系拒否権フラグ（現状は常に False）。

    TODO 実装時の条件名（観測事実・閾値のみ。主観断定・未来情報禁止）:

    race_video_veto を True にしうる条件:
    - RACE_VIDEO_HARD_TAG_VETO … 事前定義の「買い不可」主タグ集合への一致
    - RACE_VIDEO_RECURRENCE_HIGH_VETO … 同一主タグの再発度が high（recurrence モジュール）

    paddock_veto を True にしうる条件:
    - PADDOCK_DANGER_SCORE_OVER_THRESHOLD … danger スコアが閾値超過
    - PADDOCK_ALERT_FLAG_SET … alert 相当のブールが真

    warmup_veto を True にしうる条件:
    - WARMUP_ANOMALY_SCORE_OVER_THRESHOLD … anomaly スコアが閾値超過
    - WARMUP_ALERT_FLAG_SET … alert 相当のブールが真
    """
    _ = raw
    _ = race_tags
    _ = paddock_observation
    _ = warmup_observation
    return (False, False, False)


def _normalize_all(
    raw: RawSubsystemScores,
    *,
    core_src: tuple[float, float],
    race_src: tuple[float, float],
    paddock_src: tuple[float, float],
    warmup_src: tuple[float, float],
    track_bias_src: tuple[float, float],
    wind_src: tuple[float, float],
    historical_bias_src: tuple[float, float],
) -> dict[str, float]:
    norm: dict[str, float] = {}
    c = safe_normalize_core_score(raw.core, src_low=core_src[0], src_high=core_src[1])
    if c is not None:
        norm["core"] = c
    r = safe_normalize_race_score(raw.race, src_low=race_src[0], src_high=race_src[1])
    if r is not None:
        norm["race"] = r
    p = safe_normalize_paddock_score(raw.paddock, src_low=paddock_src[0], src_high=paddock_src[1])
    if p is not None:
        norm["paddock"] = p
    w = safe_normalize_warmup_score(raw.warmup, src_low=warmup_src[0], src_high=warmup_src[1])
    if w is not None:
        norm["warmup"] = w
    tb = safe_rescale_to_band(
        raw.track_bias_score,
        src_low=track_bias_src[0],
        src_high=track_bias_src[1],
    )
    if tb is not None:
        norm["track_bias_score"] = tb
    ws = safe_rescale_to_band(raw.wind_score, src_low=wind_src[0], src_high=wind_src[1])
    if ws is not None:
        norm["wind_score"] = ws
    hb = safe_rescale_to_band(
        raw.historical_bias_score,
        src_low=historical_bias_src[0],
        src_high=historical_bias_src[1],
    )
    if hb is not None:
        norm["historical_bias_score"] = hb
    return norm


def _raw_subsystem_line(
    name: str,
    raw_val: float | None,
    norm: dict[str, float],
) -> tuple[str, str]:
    key = f"raw_{name}"
    if raw_val is None:
        return (key, "missing")
    if name not in norm:
        return (key, "not_normalized")
    return (key, "normalized")


def _advisory_module_explain(norm_key: str, norm: dict[str, float]) -> str:
    """Track Bias / Wind 用（正規化値の有無と Gate 非連動）。"""
    v = norm.get(norm_key)
    base = f"module={norm_key}|feeds_gate=false"
    if v is None:
        return f"{base}|normalized_score=missing"
    return f"{base}|normalized_score={v:.4f}"


def _advisory_historical_bias_explain(norm: dict[str, float]) -> str:
    """Historical Bias の位置づけ（セル集計・M0–M3・Gate 未接続）。"""
    v = norm.get("historical_bias_score")
    parts = [
        "module=historical_bias",
        "role=bias_table_cells_advisory_only",
        "lifecycle=M0_waiting_data_until_30R_then_M1",
        "feeds_gate=false",
        "GateRuleInput_excludes_this_score",
    ]
    if v is None:
        parts.append("normalized_score=none_ui_show_reference_only")
    else:
        parts.append(f"normalized_score={v:.4f}")
    return "|".join(parts)


def _build_integration_explain(
    *,
    mode: IntegrationMode,
    raw: RawSubsystemScores,
    norm: dict[str, float],
    rv: bool,
    pv: bool,
    wv: bool,
    gate: GateRuleResult,
) -> tuple[tuple[str, str], ...]:
    parts: list[tuple[str, str]] = [
        ("integration_mode", mode.value),
        _raw_subsystem_line("core", raw.core, norm),
        _raw_subsystem_line("race", raw.race, norm),
        _raw_subsystem_line("paddock", raw.paddock, norm),
        _raw_subsystem_line("warmup", raw.warmup, norm),
        _raw_subsystem_line("track_bias_score", raw.track_bias_score, norm),
        _raw_subsystem_line("wind_score", raw.wind_score, norm),
        _raw_subsystem_line("historical_bias_score", raw.historical_bias_score, norm),
        ("advisory_slot_track_bias", _advisory_module_explain("track_bias_score", norm)),
        ("advisory_slot_wind", _advisory_module_explain("wind_score", norm)),
        (
            "advisory_slot_historical_bias",
            _advisory_historical_bias_explain(norm),
        ),
        (
            "advisory_gate_firewall",
            "track_bias|wind|historical_bias: not passed to GateRuleInput",
        ),
        ("normalized_keys", ",".join(sorted(norm))),
        ("veto_race_video", str(rv)),
        ("veto_paddock", str(pv)),
        ("veto_warmup", str(wv)),
        ("gate_bet", str(gate.bet)),
    ]
    if gate.no_bet_reasons:
        parts.append(
            ("gate_no_bet_codes", ",".join(x.value for x in gate.no_bet_reasons)),
        )
    if gate.bet_reasons:
        parts.append(("gate_bet_codes", ",".join(x.value for x in gate.bet_reasons)))
    return tuple(parts)


def _gate_input_for_mode(
    norm: dict[str, float],
    *,
    mode: IntegrationMode,
    rv: bool,
    pv: bool,
    wv: bool,
    require_core: bool,
) -> GateRuleInput:
    core = norm.get("core")
    if mode == IntegrationMode.ADVISORY:
        return GateRuleInput(
            core=core,
            race=None,
            paddock=None,
            warmup=None,
            race_video_veto=rv,
            paddock_veto=pv,
            warmup_veto=wv,
            require_core=require_core,
        )
    return GateRuleInput(
        core=core,
        race=norm.get("race"),
        paddock=norm.get("paddock"),
        warmup=norm.get("warmup"),
        race_video_veto=rv,
        paddock_veto=pv,
        warmup_veto=wv,
        require_core=require_core,
    )


def build_integration_decision(
    raw: RawSubsystemScores,
    *,
    mode: IntegrationMode = IntegrationMode.INTEGRATED,
    require_core: bool = True,
    core_src: tuple[float, float] = (-1.0, 1.0),
    race_src: tuple[float, float] = (-1.0, 1.0),
    paddock_src: tuple[float, float] = (-1.0, 1.0),
    warmup_src: tuple[float, float] = (-1.0, 1.0),
    track_bias_src: tuple[float, float] = (-1.0, 1.0),
    wind_src: tuple[float, float] = (-1.0, 1.0),
    historical_bias_src: tuple[float, float] = (-1.0, 1.0),
) -> IntegrationDecision:
    """生スコアを [-2,2] に揃え（非有限は省略）、拒否権経由で Gate を評価する。

    Core のみ有限で他が欠損・非有限でも、require_core が真なら Gate は Core 単独で成立する。

    TODO（Track Bias / Wind / Historical Bias）:
    - track_bias_score / wind_score / historical_bias_score は normalized にのみ格納し、
      Gate 集約・拒否権・重み付けには未接続（モジュール実装後に統合ロジックへ合流）。
    """
    norm = _normalize_all(
        raw,
        core_src=core_src,
        race_src=race_src,
        paddock_src=paddock_src,
        warmup_src=warmup_src,
        track_bias_src=track_bias_src,
        wind_src=wind_src,
        historical_bias_src=historical_bias_src,
    )
    rv, pv, wv = resolve_video_veto_flags(raw=raw)
    gate_in = _gate_input_for_mode(
        norm,
        mode=mode,
        rv=rv,
        pv=pv,
        wv=wv,
        require_core=require_core,
    )
    gate_result = evaluate_gate_minimal(gate_in)
    explain = _build_integration_explain(
        mode=mode,
        raw=raw,
        norm=norm,
        rv=rv,
        pv=pv,
        wv=wv,
        gate=gate_result,
    )
    return IntegrationDecision(
        mode=mode,
        normalized=dict(norm),
        race_video_veto=rv,
        paddock_veto=pv,
        warmup_veto=wv,
        gate=gate_result,
        explain=explain,
    )


__all__ = [
    "IntegrationDecision",
    "IntegrationMode",
    "RawSubsystemScores",
    "build_integration_decision",
    "resolve_video_veto_flags",
]
