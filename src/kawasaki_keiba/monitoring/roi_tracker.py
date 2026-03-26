"""最小 ROI 集計。

JudgmentLog のリストから ROI を算出し、MonitoringSnapshot を生成する。

no_bet_rate 等はスキーマ拡張なしでログ列から派生させる拡張指標として
collect_extended_monitoring_metrics に集約する（スナップショット本体は据え置き）。
"""

from __future__ import annotations

from datetime import datetime

from kawasaki_keiba.schemas.judgment_log import JudgmentLog, MonitoringSnapshot

# 強制停止閾値: 直近 ROI がこれを下回ったら halt
DEFAULT_HALT_THRESHOLD = 0.70
# 強制停止判定に必要な最小レース数
MIN_RACES_FOR_HALT = 20

# MonitoringSnapshot に無いが、同一 logs から算出しうる拡張指標キー（将来 DB/CLI 接続用）
EXTENDED_MONITORING_METRIC_KEYS: tuple[str, ...] = (
    "no_bet_rate",
    "conflict_rate",
)


def no_bet_rate(logs: list[JudgmentLog]) -> float:
    """bet_placed が False の割合。"""
    if not logs:
        return 0.0
    return sum(1 for log in logs if not log.bet_placed) / len(logs)


def collect_extended_monitoring_metrics(
    logs: list[JudgmentLog],
) -> dict[str, float | None]:
    """ROI 以外の監視値（土台）。conflict_rate は将来実装で None が解消される想定。"""
    return {
        "no_bet_rate": no_bet_rate(logs),
        "conflict_rate": None,
    }


def calculate_roi(logs: list[JudgmentLog]) -> tuple[int, int]:
    """投資額・回収額を集計する。

    Returns:
        (total_invested, total_returned)
    """
    invested = 0
    returned = 0
    for log in logs:
        if log.bet_placed and log.bet_amount is not None:
            invested += log.bet_amount
            returned += log.payout or 0
    return invested, returned


def build_monitoring_snapshot(
    logs: list[JudgmentLog],
    *,
    recent_window: int = 30,
    halt_threshold: float = DEFAULT_HALT_THRESHOLD,
) -> MonitoringSnapshot:
    """JudgmentLog リストから MonitoringSnapshot を生成する。

    Args:
        logs: 全判定ログ（古い順）
        recent_window: 直近 ROI 算出用の窓サイズ
        halt_threshold: 強制停止 ROI 閾値

    Note:
        no_bet_rate 等は collect_extended_monitoring_metrics を参照。
    """
    total_bets = sum(1 for log in logs if log.bet_placed)
    total_no_bets = len(logs) - total_bets

    total_invested, total_returned = calculate_roi(logs)
    roi = total_returned / total_invested if total_invested > 0 else 0.0

    # 直近 N レースの ROI
    recent_roi: float | None = None
    if len(logs) >= recent_window:
        recent_logs = logs[-recent_window:]
        r_inv, r_ret = calculate_roi(recent_logs)
        recent_roi = r_ret / r_inv if r_inv > 0 else None

    # TODO: Core vs 映像系の衝突率（Phase 3-4 で映像系統合後に実装）
    conflict_rate: float | None = None

    # 強制停止判定
    halt_active = False
    halt_reason: str | None = None
    if recent_roi is not None and total_bets >= MIN_RACES_FOR_HALT and recent_roi < halt_threshold:
        halt_active = True
        halt_reason = (
            f"直近{recent_window}レース ROI {recent_roi:.2f} "
            f"< 閾値 {halt_threshold:.2f}"
        )

    return MonitoringSnapshot(
        timestamp=datetime.now(),
        total_bets=total_bets,
        total_no_bets=total_no_bets,
        total_invested=total_invested,
        total_returned=total_returned,
        roi=roi,
        recent_roi_30=recent_roi,
        conflict_rate=conflict_rate,
        halt_active=halt_active,
        halt_reason=halt_reason,
    )
