"""Track Bias モジュールのテスト"""

from datetime import date

from kawasaki_keiba.schemas.race import (
    HorseEntry,
    RaceGrade,
    RaceRecord,
    RaceResult,
    TrackCondition,
)
from kawasaki_keiba.track_bias.compute import (
    compute_pace_bias,
    compute_post_bias,
    compute_track_bias,
)
from kawasaki_keiba.track_bias.snapshot import TrackBiasSnapshot


def _race(race_id: str = "20260401_KW_07", num_runners: int = 10) -> RaceRecord:
    return RaceRecord(
        race_id=race_id,
        race_date=date(2026, 4, 1),
        race_number=7,
        distance=1400,
        track_condition=TrackCondition.GOOD,
        grade=RaceGrade.B2,
        num_runners=num_runners,
    )


def _entries(n: int = 10, race_id: str = "20260401_KW_07") -> list[HorseEntry]:
    # 人気順をシャッフル（枠番と人気を非相関にする）
    # 例: 枠1→人気5, 枠2→人気3, ... 内枠の人気が必ずしも高くない
    pops = list(range(1, n + 1))
    # 簡易シャッフル: 偶数番と奇数番を入れ替え
    shuffled = [0] * n
    for i in range(n):
        shuffled[i] = pops[(i * 7 + 3) % n]
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
            popularity=shuffled[i - 1],
        )
        for i in range(1, n + 1)
    ]


def _results(
    n: int = 10,
    race_id: str = "20260401_KW_07",
    inner_wins: bool = True,
) -> list[RaceResult]:
    """inner_wins=True なら内枠が好走するデータを生成。"""
    if inner_wins:
        positions = list(range(1, n + 1))  # 内枠=1着, 外枠=最下位
    else:
        positions = list(range(n, 0, -1))  # 外枠=1着
    return [
        RaceResult(
            race_id=race_id,
            horse_id=f"H{i:03d}",
            horse_number=i,
            finish_position=positions[i - 1],
            corner_positions=f"{positions[i - 1]}-{positions[i - 1]}",
        )
        for i in range(1, n + 1)
    ]


class TestPostBias:
    def test_inner_advantage(self):
        entries = _entries(10)
        results = _results(10, inner_wins=True)
        bias = compute_post_bias(entries, results)
        # 内枠が好走 → 負の値（内有利）
        assert bias < 0

    def test_outer_advantage(self):
        entries = _entries(10)
        results = _results(10, inner_wins=False)
        bias = compute_post_bias(entries, results)
        # 外枠が好走 → 正の値（外有利）
        assert bias > 0

    def test_empty_data(self):
        assert compute_post_bias([], []) == 0.0

    def test_small_field_returns_zero(self):
        entries = _entries(4)
        results = _results(4)
        assert compute_post_bias(entries, results) == 0.0


class TestPaceBias:
    def test_front_advantage(self):
        # 先行勢（1角通過上位）が好走
        results = [
            RaceResult(
                race_id="R", horse_id=f"H{i}", horse_number=i,
                finish_position=i, corner_positions=f"{i}-{i}",
            )
            for i in range(1, 11)
        ]
        bias = compute_pace_bias(results, 10)
        # 先行=好走 → 負の値
        assert bias < 0

    def test_closer_advantage(self):
        # 差し勢（1角通過下位）が好走
        results = [
            RaceResult(
                race_id="R", horse_id=f"H{i}", horse_number=i,
                finish_position=11 - i, corner_positions=f"{i}-{i}",
            )
            for i in range(1, 11)
        ]
        bias = compute_pace_bias(results, 10)
        # 差し=好走 → 正の値
        assert bias > 0

    def test_no_corners(self):
        results = [
            RaceResult(race_id="R", horse_id="H1", horse_number=1, finish_position=1)
        ]
        assert compute_pace_bias(results, 10) == 0.0


class TestTrackBiasSnapshot:
    def test_bias_direction(self):
        snap = TrackBiasSnapshot(
            race_date=date(2026, 4, 1), distance=1400,
            track_condition=TrackCondition.GOOD,
            computed_after_race=5,
            post_bias=-0.5, pace_bias=-0.3,
            post_confidence=0.5, pace_confidence=0.4,
            sample_races=5, short_reason="test",
        )
        assert "内枠有利" in snap.bias_direction
        assert "先行有利" in snap.bias_direction

    def test_no_bias(self):
        snap = TrackBiasSnapshot(
            race_date=date(2026, 4, 1), distance=1400,
            track_condition=TrackCondition.GOOD,
            computed_after_race=2,
            post_bias=0.05, pace_bias=-0.1,
            post_confidence=0.1, pace_confidence=0.1,
            sample_races=2, short_reason="test",
        )
        assert snap.bias_direction == "顕著な傾向なし"

    def test_score_range(self):
        snap = TrackBiasSnapshot(
            race_date=date(2026, 4, 1), distance=1400,
            track_condition=TrackCondition.GOOD,
            computed_after_race=10,
            post_bias=-1.0, pace_bias=-1.0,
            post_confidence=1.0, pace_confidence=1.0,
            sample_races=12, short_reason="test",
        )
        score = snap.to_score()
        assert -2.0 <= score <= 2.0

    def test_to_dict(self):
        snap = TrackBiasSnapshot(
            race_date=date(2026, 4, 1), distance=1400,
            track_condition=TrackCondition.GOOD,
            computed_after_race=5,
            post_bias=-0.3, pace_bias=0.1,
            post_confidence=0.5, pace_confidence=0.3,
            sample_races=5, short_reason="test",
        )
        d = snap.to_dict()
        assert "post_bias" in d
        assert "bias_direction" in d
        assert "score" in d


class TestComputeTrackBias:
    def test_empty_races(self):
        snap = compute_track_bias([], {}, {})
        assert snap.sample_races == 0
        assert snap.short_reason == "レース結果なし"

    def test_with_races(self):
        races = [_race(f"20260401_KW_{i:02d}") for i in range(1, 6)]
        entries = {r.race_id: _entries(10, r.race_id) for r in races}
        results = {r.race_id: _results(10, r.race_id, inner_wins=True) for r in races}

        snap = compute_track_bias(races, entries, results)
        assert snap.sample_races > 0
        assert snap.post_bias < 0  # 内有利データ
