"""スキーマのバリデーションテスト"""

from datetime import date

import pytest

from kawasaki_keiba.schemas.prediction import (
    CorePrediction,
    GateDecision,
    NoBetReason,
    RaceVideoTag,
    VideoObservation,
)
from kawasaki_keiba.schemas.race import RaceGrade, RaceRecord, TrackCondition


class TestRaceRecord:
    def test_valid(self):
        r = RaceRecord(
            race_id="20260301_KW_07",
            race_date=date(2026, 3, 1),
            race_number=7,
            distance=1500,
            track_condition=TrackCondition.GOOD,
            grade=RaceGrade.B2,
            num_runners=12,
        )
        assert r.race_id == "20260301_KW_07"

    def test_invalid_race_id(self):
        with pytest.raises(ValueError):
            RaceRecord(
                race_id="20260301_OI_07",  # 大井は不正
                race_date=date(2026, 3, 1),
                race_number=7,
                distance=1500,
                track_condition=TrackCondition.GOOD,
                grade=RaceGrade.B2,
                num_runners=12,
            )

    def test_race_number_range(self):
        with pytest.raises(ValueError):
            RaceRecord(
                race_id="20260301_KW_13",
                race_date=date(2026, 3, 1),
                race_number=13,  # 1-12の範囲外
                distance=1500,
                track_condition=TrackCondition.GOOD,
                grade=RaceGrade.B2,
                num_runners=12,
            )


class TestCorePrediction:
    def test_valid(self):
        p = CorePrediction(
            race_id="20260301_KW_07",
            horse_id="H001",
            horse_number=5,
            rank_score=0.85,
            win_prob=0.15,
            place_prob=0.45,
            market_win_prob=0.10,
            edge_win=0.05,
            edge_place=0.10,
        )
        assert p.edge_win == 0.05

    def test_prob_range(self):
        with pytest.raises(ValueError):
            CorePrediction(
                race_id="20260301_KW_07",
                horse_id="H001",
                horse_number=5,
                rank_score=0.85,
                win_prob=1.5,  # 範囲外
                place_prob=0.45,
                market_win_prob=0.10,
                edge_win=0.05,
                edge_place=0.10,
            )


class TestGateDecision:
    def test_no_bet(self):
        d = GateDecision(
            race_id="20260301_KW_07",
            decision="no_bet",
            no_bet_reasons=[NoBetReason.NO_EDGE, NoBetReason.SMALL_FIELD],
            confidence=0.8,
        )
        assert d.decision == "no_bet"
        assert len(d.no_bet_reasons) == 2


class TestVideoObservation:
    def test_tags(self):
        v = VideoObservation(
            race_id="20260301_KW_07",
            horse_id="H001",
            horse_number=5,
            tags=[RaceVideoTag.POSITION_FRONT, RaceVideoTag.FADING, RaceVideoTag.LOSS_PACE],
            comment="先行 → 直線失速 → ペースが合わず",
            recurrence_score=0.3,
        )
        assert len(v.tags) == 3
        assert v.recurrence_score == 0.3
