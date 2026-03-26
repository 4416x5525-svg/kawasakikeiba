"""Historical Bias (bias_table) のテスト"""

from datetime import date

from kawasaki_keiba.core.bias_table import (
    BiasCell,
    build_bias_table,
    historical_bias_adjustment,
    lookup_bias,
)
from kawasaki_keiba.schemas.race import (
    HorseEntry,
    RaceGrade,
    RaceRecord,
    RaceResult,
    TrackCondition,
)


def _make_races(n: int = 20) -> list[RaceRecord]:
    """テスト用レースリスト。"""
    races = []
    for i in range(n):
        day = 1 + (i // 12)
        race_num = (i % 12) + 1
        races.append(
            RaceRecord(
                race_id=f"202604{day:02d}_KW_{race_num:02d}",
                race_date=date(2026, 4, day),
                race_number=race_num,
                distance=1400,
                track_condition=TrackCondition.GOOD,
                grade=RaceGrade.C2,
                num_runners=10,
            )
        )
    return races


def _make_entries(race_id: str, n: int = 10) -> list[HorseEntry]:
    return [
        HorseEntry(
            race_id=race_id,
            horse_id=f"H{i:03d}",
            horse_name=f"Horse{i}",
            post_position=i,
            horse_number=i,
            jockey_id=f"J{i:03d}",
            jockey_name=f"Jockey{i}",
            trainer_id=f"T{i:03d}",
            weight_carried=55.0,
            popularity=i,
        )
        for i in range(1, n + 1)
    ]


def _make_results(race_id: str, n: int = 10) -> list[RaceResult]:
    """内枠有利のデータ。"""
    return [
        RaceResult(
            race_id=race_id,
            horse_id=f"H{i:03d}",
            horse_number=i,
            finish_position=i,
            corner_positions=f"{i}-{i}",
        )
        for i in range(1, n + 1)
    ]


class TestBiasCell:
    def test_confidence_low_sample(self):
        cell = BiasCell(
            distance_group="mid", condition_group="good", field_size_group="normal",
            inner_win_rate=0.15, outer_win_rate=0.08,
            inner_advantage=0.07,
            front_place_rate=0.45, closer_place_rate=0.30,
            pace_advantage=0.15,
            sample_races=10,
            sample_period="2026-04-01 to 2026-04-10",
            significant_post=True, significant_pace=True,
        )
        assert cell.confidence == 0.0  # < 15 races

    def test_confidence_sufficient_sample(self):
        cell = BiasCell(
            distance_group="mid", condition_group="good", field_size_group="normal",
            inner_win_rate=0.15, outer_win_rate=0.08,
            inner_advantage=0.07,
            front_place_rate=0.45, closer_place_rate=0.30,
            pace_advantage=0.15,
            sample_races=50,
            sample_period="2026-01 to 2026-04",
            significant_post=True, significant_pace=True,
        )
        assert cell.confidence > 0.0

    def test_short_reason_with_bias(self):
        cell = BiasCell(
            distance_group="mid", condition_group="good", field_size_group="normal",
            inner_win_rate=0.15, outer_win_rate=0.08,
            inner_advantage=0.07,
            front_place_rate=0.45, closer_place_rate=0.30,
            pace_advantage=0.15,
            sample_races=50,
            sample_period="test",
            significant_post=True, significant_pace=True,
        )
        reason = cell.short_reason()
        assert "内枠有利" in reason
        assert "先行有利" in reason

    def test_to_dict(self):
        cell = BiasCell(
            distance_group="mid", condition_group="good", field_size_group="normal",
            inner_win_rate=0.12, outer_win_rate=0.10,
            inner_advantage=0.02,
            front_place_rate=0.40, closer_place_rate=0.35,
            pace_advantage=0.05,
            sample_races=30,
            sample_period="test",
            significant_post=False, significant_pace=True,
        )
        d = cell.to_dict()
        assert "confidence" in d
        assert "short_reason" in d


class TestBuildBiasTable:
    def test_builds_table(self):
        races = _make_races(20)
        entries = {r.race_id: _make_entries(r.race_id) for r in races}
        results = {r.race_id: _make_results(r.race_id) for r in races}

        table = build_bias_table(races, entries, results)
        assert len(table) > 0

        # "mid", "good", "normal" セルが存在するはず
        cell = lookup_bias(table, 1400, TrackCondition.GOOD, 10)
        assert cell is not None
        assert cell.sample_races == 20

    def test_empty_data(self):
        table = build_bias_table([], {}, {})
        assert len(table) == 0

    def test_min_date_filter(self):
        races = _make_races(20)
        entries = {r.race_id: _make_entries(r.race_id) for r in races}
        results = {r.race_id: _make_results(r.race_id) for r in races}

        # min_date を未来に設定 → 全レース除外
        table = build_bias_table(
            races, entries, results, min_date=date(2027, 1, 1)
        )
        assert len(table) == 0


class TestHistoricalBiasAdjustment:
    def test_inner_advantage_for_inner_post(self):
        cell = BiasCell(
            distance_group="mid", condition_group="good", field_size_group="normal",
            inner_win_rate=0.15, outer_win_rate=0.08,
            inner_advantage=0.07,
            front_place_rate=0.40, closer_place_rate=0.35,
            pace_advantage=0.05,
            sample_races=100,
            sample_period="test",
            significant_post=True, significant_pace=False,
        )
        adj = historical_bias_adjustment(cell, post_position=2, num_runners=10)
        assert adj > 0  # 内枠 + 内有利 → 正の補正

    def test_inner_advantage_for_outer_post(self):
        cell = BiasCell(
            distance_group="mid", condition_group="good", field_size_group="normal",
            inner_win_rate=0.15, outer_win_rate=0.08,
            inner_advantage=0.07,
            front_place_rate=0.40, closer_place_rate=0.35,
            pace_advantage=0.05,
            sample_races=100,
            sample_period="test",
            significant_post=True, significant_pace=False,
        )
        adj = historical_bias_adjustment(cell, post_position=9, num_runners=10)
        assert adj < 0  # 外枠 + 内有利 → 負の補正

    def test_none_cell(self):
        assert historical_bias_adjustment(None, 1, 10) == 0.0

    def test_adjustment_bounded(self):
        cell = BiasCell(
            distance_group="mid", condition_group="good", field_size_group="normal",
            inner_win_rate=0.30, outer_win_rate=0.01,
            inner_advantage=0.29,
            front_place_rate=0.80, closer_place_rate=0.05,
            pace_advantage=0.75,
            sample_races=200,
            sample_period="test",
            significant_post=True, significant_pace=True,
        )
        adj = historical_bias_adjustment(cell, 1, 10, "front")
        assert -0.5 <= adj <= 0.5
