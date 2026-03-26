"""Gate 用理由コード（ルールベース土台）。"""

from __future__ import annotations

from enum import StrEnum


class NoBetReasonCode(StrEnum):
    """no-bet 理由コード。"""

    # スコア・シグナル
    WEAK_CORE = "weak_core"
    WEAK_AGGREGATE = "weak_aggregate"
    INSUFFICIENT_SIGNAL = "insufficient_signal"

    # データ・前提
    MISSING_REQUIRED_SCORE = "missing_required_score"

    # 映像系（拒否権は integration 側でフラグ化 → Gate で集約）
    VIDEO_VETO = "video_veto"
    PADDOCK_VETO = "paddock_veto"
    WARMUP_VETO = "warmup_veto"

    # 監視・運用（将来接続）
    MONITORING_HALT = "monitoring_halt"


class BetReasonCode(StrEnum):
    """bet 理由コード。"""

    RULE_PASS = "rule_pass"
    CORE_SUPPORT = "core_support"
    CONSENSUS_SUPPORT = "consensus_support"
