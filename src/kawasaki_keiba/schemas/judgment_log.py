"""判定ログのスキーマ定義"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .prediction import (
    BetReason,
    NoBetReason,
)


class JudgmentLog(BaseModel):
    """1レースの最終判定ログ（保存対象）"""
    race_id: str
    timestamp: datetime = Field(default_factory=datetime.now)

    # Core 出力サマリ
    core_predictions: list[dict[str, Any]] = Field(
        description="各馬の rank_score, win_prob, place_prob, edge"
    )

    # Gate 判定
    gate_decision: str = Field(description="'bet' or 'no_bet'")
    no_bet_reasons: list[NoBetReason] = Field(default_factory=list)
    bet_reasons: list[BetReason] = Field(default_factory=list)
    gate_confidence: float

    # 映像系（advisory / integrated の場合のみ）
    video_tags: list[dict[str, Any]] | None = None
    paddock_summary: list[dict[str, Any]] | None = None
    warmup_summary: list[dict[str, Any]] | None = None

    # 統合スコア
    integrated_scores: list[dict[str, Any]] | None = None

    # 実際のアクション
    bet_placed: bool = False
    bet_type: str | None = None
    bet_amount: int | None = None
    bet_target: list[int] | None = Field(default=None, description="対象馬番リスト")

    # 事後
    result_position: int | None = None
    payout: int | None = None
    profit: int | None = None


class MonitoringSnapshot(BaseModel):
    """監視スナップショット"""
    timestamp: datetime = Field(default_factory=datetime.now)
    total_bets: int
    total_no_bets: int
    total_invested: int
    total_returned: int
    roi: float = Field(description="ROI = total_returned / total_invested")
    recent_roi_30: float | None = Field(
        default=None, description="直近30レースROI"
    )
    conflict_rate: float | None = Field(
        default=None, description="Core vs 映像系 衝突率"
    )
    halt_active: bool = Field(default=False, description="強制停止中フラグ")
    halt_reason: str | None = None
