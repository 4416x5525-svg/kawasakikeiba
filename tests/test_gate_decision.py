"""Gate decision (CorePrediction → GateDecision) のテスト"""

from datetime import date

from kawasaki_keiba.gate.decision import (
    aggregate_core_score,
    check_race_conditions,
    run_gate,
)
from kawasaki_keiba.schemas.prediction import CorePrediction, NoBetReason
from kawasaki_keiba.schemas.race import RaceGrade, RaceRecord, TrackCondition


def _make_race(num_runners: int = 10) -> RaceRecord:
    return RaceRecord(
        race_id="20260301_KW_07",
        race_date=date(2026, 3, 1),
        race_number=7,
        distance=1500,
        track_condition=TrackCondition.GOOD,
        grade=RaceGrade.B2,
        num_runners=num_runners,
    )


def _make_predictions(
    n: int = 10,
    edge_win: float = 0.05,
    market_prob: float = 0.1,
    *,
    all_same_edge: bool = False,
) -> list[CorePrediction]:
    """テスト用 CorePrediction リスト。

    all_same_edge=True の場合、全馬に同じ edge を設定。
    False の場合、1番馬にのみ edge を設定、他は減衰。
    """
    return [
        CorePrediction(
            race_id="20260301_KW_07",
            horse_id=f"H{i:03d}",
            horse_number=i,
            rank_score=1.0 - (i - 1) / max(n - 1, 1),
            win_prob=max(0.0, min(1.0, market_prob + _edge_for(i, n, edge_win, all_same_edge))),
            place_prob=0.3,
            market_win_prob=market_prob,
            edge_win=_edge_for(i, n, edge_win, all_same_edge),
            edge_place=0.05 if i == 1 else 0.0,
        )
        for i in range(1, n + 1)
    ]


def _edge_for(i: int, n: int, edge_win: float, all_same: bool) -> float:
    if all_same:
        return edge_win
    # 1番馬に最大 edge、他は線形減衰
    return edge_win * (1.0 - (i - 1) / max(n - 1, 1))


class TestAggregateCoreScore:
    def test_positive_edge(self):
        preds = _make_predictions(edge_win=0.08)
        score = aggregate_core_score(preds)
        assert score is not None
        assert score > 0.0  # 正の edge → 正のスコア

    def test_negative_edge(self):
        preds = _make_predictions(edge_win=-0.05, all_same_edge=True)
        score = aggregate_core_score(preds)
        assert score is not None
        assert score < 0.0

    def test_empty_predictions(self):
        assert aggregate_core_score([]) is None

    def test_clipping(self):
        preds = _make_predictions(edge_win=0.5)  # 大きな edge
        score = aggregate_core_score(preds)
        assert score is not None
        assert score == 2.0  # [-2, 2] の上限でクリップ


class TestCheckRaceConditions:
    def test_small_field(self):
        race = _make_race(num_runners=4)
        preds = _make_predictions(n=4)
        reasons = check_race_conditions(preds, race)
        assert NoBetReason.SMALL_FIELD in reasons

    def test_normal_field_no_issues(self):
        race = _make_race(num_runners=10)
        preds = _make_predictions(n=10)
        reasons = check_race_conditions(preds, race)
        assert len(reasons) == 0

    def test_insufficient_odds_data(self):
        race = _make_race(num_runners=8)
        preds = _make_predictions(n=8, market_prob=0.0)  # market_prob=0 → no odds
        reasons = check_race_conditions(preds, race)
        assert NoBetReason.INSUFFICIENT_DATA in reasons


class TestRunGate:
    def test_positive_edge_bets(self):
        race = _make_race()
        preds = _make_predictions(edge_win=0.08)
        decision = run_gate(preds, race)
        assert decision.decision == "bet"
        assert len(decision.bet_reasons) > 0

    def test_no_edge_no_bet(self):
        race = _make_race()
        preds = _make_predictions(edge_win=-0.08, all_same_edge=True)
        decision = run_gate(preds, race)
        assert decision.decision == "no_bet"
        assert len(decision.no_bet_reasons) > 0

    def test_small_field_no_bet(self):
        race = _make_race(num_runners=3)
        preds = _make_predictions(n=3, edge_win=0.08)
        decision = run_gate(preds, race)
        assert decision.decision == "no_bet"
        assert NoBetReason.SMALL_FIELD in decision.no_bet_reasons

    def test_video_veto_overrides(self):
        race = _make_race()
        preds = _make_predictions(edge_win=0.08)
        decision = run_gate(preds, race, race_video_veto=True)
        assert decision.decision == "no_bet"
        assert NoBetReason.VIDEO_VETO in decision.no_bet_reasons

    def test_paddock_veto_overrides(self):
        race = _make_race()
        preds = _make_predictions(edge_win=0.08)
        decision = run_gate(preds, race, paddock_veto=True)
        assert decision.decision == "no_bet"
        assert NoBetReason.PADDOCK_ALERT in decision.no_bet_reasons

    def test_warmup_veto_overrides(self):
        race = _make_race()
        preds = _make_predictions(edge_win=0.08)
        decision = run_gate(preds, race, warmup_veto=True)
        assert decision.decision == "no_bet"
        assert NoBetReason.WARMUP_ALERT in decision.no_bet_reasons

    def test_core_only_without_video_systems(self):
        """映像系未入力でも Core のみで判定が動く"""
        race = _make_race()
        preds = _make_predictions(edge_win=0.06)
        decision = run_gate(preds, race)
        assert decision.race_id == "20260301_KW_07"
        assert decision.decision in ("bet", "no_bet")

    def test_with_optional_scores(self):
        """映像系スコアを渡しても正常動作する"""
        race = _make_race()
        preds = _make_predictions(edge_win=0.06)
        decision = run_gate(
            preds, race,
            race_score=0.5,
            paddock_score=0.3,
            warmup_score=0.2,
        )
        assert decision.decision in ("bet", "no_bet")
