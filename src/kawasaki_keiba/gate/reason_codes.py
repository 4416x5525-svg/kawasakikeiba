"""Gate 用理由コード（ルールベース土台）。

区分（NoBet）:
  A. スコア・集約 … WEAK_CORE, WEAK_AGGREGATE, INSUFFICIENT_SIGNAL
  B. 必須入力 … MISSING_REQUIRED_SCORE
  C. 映像系拒否権（integration が立てたフラグ）… VIDEO_VETO, PADDOCK_VETO, WARMUP_VETO
  D. 運用 … MONITORING_HALT

区分（Bet）:
  E. ゲート通過 … RULE_PASS
  F. Core 寄与 … CORE_SUPPORT
  G. 全サブシステム非負のとき … CONSENSUS_SUPPORT
"""

from __future__ import annotations

from enum import StrEnum


class NoBetReasonCode(StrEnum):
    """no-bet 理由コード（上記区分 A–D）。"""

    # --- A: スコア・集約 ---
    WEAK_CORE = "weak_core"
    WEAK_AGGREGATE = "weak_aggregate"
    INSUFFICIENT_SIGNAL = "insufficient_signal"

    # --- B: 必須入力 ---
    MISSING_REQUIRED_SCORE = "missing_required_score"

    # --- C: 映像系拒否権（フラグは integration.resolve_video_veto_flags 側）---
    VIDEO_VETO = "video_veto"
    PADDOCK_VETO = "paddock_veto"
    WARMUP_VETO = "warmup_veto"

    # --- D: 運用 ---
    MONITORING_HALT = "monitoring_halt"


class BetReasonCode(StrEnum):
    """bet 理由コード（上記区分 E–G）。"""

    RULE_PASS = "rule_pass"
    CORE_SUPPORT = "core_support"
    CONSENSUS_SUPPORT = "consensus_support"
