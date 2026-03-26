"""予測・判定結果のスキーマ定義"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Core prediction
# ---------------------------------------------------------------------------

class CorePrediction(BaseModel):
    """Core モデルの予測出力（1頭分）"""
    race_id: str
    horse_id: str
    horse_number: int
    rank_score: float = Field(description="ランキングスコア（相対順位用）")
    win_prob: float = Field(ge=0, le=1, description="勝率推定値")
    place_prob: float = Field(ge=0, le=1, description="複勝圏（3着以内）推定値")
    market_win_prob: float = Field(ge=0, le=1, description="単勝オッズから逆算した市場推定勝率")
    edge_win: float = Field(description="win_prob - market_win_prob")
    edge_place: float = Field(description="place_prob - market_place_prob (推定)")


# ---------------------------------------------------------------------------
# Gate (no-bet / bet decision)
# ---------------------------------------------------------------------------

class NoBetReason(StrEnum):
    """no-bet 理由コード"""
    NO_EDGE = "no_edge"                      # edge不足
    LOW_CONFIDENCE = "low_confidence"        # モデル信頼度低
    INSUFFICIENT_DATA = "insufficient_data"  # データ不足
    TRACK_CONDITION = "track_condition"      # 馬場状態による不確実性
    SMALL_FIELD = "small_field"              # 少頭数
    CLASS_MISMATCH = "class_mismatch"        # クラス変動
    SCRATCHED_FAVORITE = "scratched_favorite"  # 人気馬取消
    VIDEO_VETO = "video_veto"                # 映像系拒否権
    PADDOCK_ALERT = "paddock_alert"          # パドック異常
    WARMUP_ALERT = "warmup_alert"            # 返し馬異常
    MONITORING_HALT = "monitoring_halt"      # ROI監視による停止


class BetReason(StrEnum):
    """bet 理由コード"""
    POSITIVE_EDGE = "positive_edge"          # 正のedge
    PACE_ADVANTAGE = "pace_advantage"        # 展開利
    CONDITION_PLUS = "condition_plus"        # 映像系プラス評価
    MARKET_INEFFICIENCY = "market_inefficiency"  # 市場非効率


class GateDecision(BaseModel):
    """Gate の判定結果"""
    race_id: str
    decision: str = Field(description="'bet' or 'no_bet'")
    no_bet_reasons: list[NoBetReason] = Field(default_factory=list)
    bet_reasons: list[BetReason] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    timestamp: datetime = Field(default_factory=datetime.now)


class CourseContextScores(BaseModel):
    """Track Bias / Wind / Historical Bias（統合帯 [-2,2]、モジュール未実装時は None）。"""

    model_config = ConfigDict(extra="forbid")

    track_bias_score: float | None = Field(default=None, ge=-2, le=2)
    wind_score: float | None = Field(default=None, ge=-2, le=2)
    historical_bias_score: float | None = Field(default=None, ge=-2, le=2)


# ---------------------------------------------------------------------------
# Video observation tags
# ---------------------------------------------------------------------------

class RaceVideoTag(StrEnum):
    """レース映像から付与するタグ（観測事実のみ）"""
    # 位置取り
    POSITION_FRONT = "position_front"          # 先行
    POSITION_MIDDLE = "position_middle"        # 中団
    POSITION_REAR = "position_rear"            # 後方
    # ペース
    PACE_FAST = "pace_fast"                    # ハイペース
    PACE_SLOW = "pace_slow"                    # スローペース
    # 走行
    WIDE_RUNNING = "wide_running"              # 外を回す
    RAIL_RUNNING = "rail_running"              # 内を走行
    BLOCKED = "blocked"                        # 前が壁
    STUMBLE = "stumble"                        # 躓き
    # 直線
    SWITCHED_LATE = "switched_late"            # 追い出し遅れ
    STRONG_FINISH = "strong_finish"            # 脚色衰えず
    FADING = "fading"                          # 脚色鈍化
    # 敗因カテゴリ
    LOSS_PACE = "loss_pace"                    # ペースが合わず
    LOSS_POSITION = "loss_position"            # 位置取り不利
    LOSS_BLOCKED = "loss_blocked"              # 進路妨害/前壁
    LOSS_CONDITION = "loss_condition"          # 馬場不適合
    # 勝因カテゴリ
    WIN_PACE_FIT = "win_pace_fit"              # ペース適合
    WIN_POSITION = "win_position"              # 好位置取り
    WIN_STRONG_KICK = "win_strong_kick"        # 末脚発揮


class VideoObservation(BaseModel):
    """レース映像観測結果（1頭分）"""
    race_id: str
    horse_id: str
    horse_number: int
    tags: list[RaceVideoTag] = Field(default_factory=list)
    comment: str = Field(default="", description="半構造化コメント（観測事実のみ）")
    recurrence_score: float | None = Field(
        default=None, ge=0, le=1,
        description="敗因/勝因の再発度（0=偶発的, 1=構造的）"
    )
    observed_at: datetime = Field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Paddock / Warmup observation
# ---------------------------------------------------------------------------

class ConditionState(StrEnum):
    GOOD = "good"
    NEUTRAL = "neutral"
    BAD = "bad"


class ConditionTrend(StrEnum):
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


class SystemMode(StrEnum):
    """映像系サブシステムの動作モード"""
    OFF = "off"
    ADVISORY = "advisory"
    INTEGRATED = "integrated"


class PaddockObservation(BaseModel):
    """パドック観測結果（1頭分）"""
    race_id: str
    horse_id: str
    horse_number: int
    state: ConditionState
    trend: ConditionTrend
    danger_popular: bool = Field(default=False, description="危険人気馬フラグ")
    tags: list[str] = Field(default_factory=list)
    comment: str = Field(default="")
    observed_at: datetime = Field(default_factory=datetime.now)


class WarmupObservation(BaseModel):
    """返し馬観測結果（1頭分）"""
    race_id: str
    horse_id: str
    horse_number: int
    state: ConditionState
    anomaly_detected: bool = Field(default=False, description="直前異常フラグ")
    tags: list[str] = Field(default_factory=list)
    comment: str = Field(default="")
    observed_at: datetime = Field(default_factory=datetime.now)
