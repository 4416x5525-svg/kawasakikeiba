"""Core scoring のテスト"""

import math
from pathlib import Path

import pytest

from kawasaki_keiba.core.scoring import (
    compute_adjustment,
    generate_core_predictions,
    market_adjusted_prob,
)
from kawasaki_keiba.data.loader import load_entries, load_races
from kawasaki_keiba.schemas.race import HorseEntry

SAMPLE_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "sample_races.json"


class TestMarketAdjustedProb:
    def test_zero_adjustment_returns_market(self):
        """adjustment=0 なら市場確率がそのまま返る。"""
        assert market_adjusted_prob(0.25, 0.0) == pytest.approx(0.25, abs=0.001)

    def test_positive_adjustment_increases_prob(self):
        """正の補正は確率を上げる。"""
        base = 0.20
        adjusted = market_adjusted_prob(base, 0.5)
        assert adjusted > base

    def test_negative_adjustment_decreases_prob(self):
        """負の補正は確率を下げる。"""
        base = 0.20
        adjusted = market_adjusted_prob(base, -0.5)
        assert adjusted < base

    def test_clamped_to_max(self):
        """極端な補正値はクランプされる。"""
        result = market_adjusted_prob(0.5, 100.0)
        assert 0 < result < 1

    def test_boundary_probs(self):
        """境界値（0に近い、1に近い）でも壊れない。"""
        assert 0 < market_adjusted_prob(0.001, 0.5) < 1
        assert 0 < market_adjusted_prob(0.999, -0.5) < 1

    def test_symmetry(self):
        """正負同量の補正は概ね対称。"""
        up = market_adjusted_prob(0.5, 0.3)
        down = market_adjusted_prob(0.5, -0.3)
        # 0.5 を中心に対称
        assert abs((up - 0.5) + (down - 0.5)) < 0.01


class TestComputeAdjustment:
    def test_no_features_returns_zero(self):
        assert compute_adjustment(None) == 0.0
        assert compute_adjustment({}) == 0.0

    def test_with_features(self):
        features = {"distance_fit": 0.5, "form_trend": 0.8}
        adj = compute_adjustment(features)
        assert adj > 0  # 正の特徴量 → 正の補正

    def test_clamped(self):
        features = {"distance_fit": 10.0, "form_trend": 10.0, "condition_fit": 10.0}
        adj = compute_adjustment(features)
        assert -1.0 <= adj <= 1.0


class TestGenerateCorePredictions:
    def test_no_features_edge_near_zero(self):
        """特徴量なし → edge ≈ 0（市場確率をそのまま返す）。"""
        races = load_races(SAMPLE_PATH)
        entries_map = load_entries(SAMPLE_PATH)
        first_id = races[0].race_id
        r_entries = entries_map[first_id]

        preds = generate_core_predictions(r_entries, features_by_horse=None)
        assert len(preds) == len(r_entries)

        # 全馬の edge が 0 に近い（逆FLB解消の確認）
        for p in preds:
            assert abs(p.edge_win) < 0.001, f"#{p.horse_number} edge={p.edge_win}"

    def test_probs_sum_to_one(self):
        """win_prob の合計が 1.0 に近い。"""
        races = load_races(SAMPLE_PATH)
        entries_map = load_entries(SAMPLE_PATH)
        first_id = races[0].race_id
        r_entries = entries_map[first_id]

        preds = generate_core_predictions(r_entries)
        total = sum(p.win_prob for p in preds)
        assert total == pytest.approx(1.0, abs=0.01)

    def test_with_features_produces_edge(self):
        """特徴量ありなら edge ≠ 0 が生じる。"""
        races = load_races(SAMPLE_PATH)
        entries_map = load_entries(SAMPLE_PATH)
        first_id = races[0].race_id
        r_entries = entries_map[first_id]

        # 1番馬に正の特徴量を与える
        features = {
            r_entries[0].horse_number: {"distance_fit": 0.8, "form_trend": 0.6},
        }
        preds = generate_core_predictions(r_entries, features_by_horse=features)

        # 1番馬の edge が正
        p1 = next(p for p in preds if p.horse_number == r_entries[0].horse_number)
        assert p1.edge_win > 0.001

        # 他の馬の edge は負（正規化で相対的に下がる）
        others = [p for p in preds if p.horse_number != r_entries[0].horse_number]
        assert any(p.edge_win < -0.001 for p in others)

    def test_rank_score_ordering(self):
        """rank_score は core_prob 降順で 1.0 → 0.0。"""
        races = load_races(SAMPLE_PATH)
        entries_map = load_entries(SAMPLE_PATH)
        first_id = races[0].race_id
        r_entries = entries_map[first_id]

        preds = generate_core_predictions(r_entries)
        sorted_preds = sorted(preds, key=lambda p: p.rank_score, reverse=True)
        # rank_score が最大の馬は win_prob も最大
        assert sorted_preds[0].win_prob >= sorted_preds[-1].win_prob

    def test_baseline_comparison(self):
        """Core scoring (adj=0) の edge が baseline の edge より遥かに小さい。"""
        from kawasaki_keiba.core.baseline import generate_baseline_predictions
        from kawasaki_keiba.core.market import market_probs_from_odds

        races = load_races(SAMPLE_PATH)
        entries_map = load_entries(SAMPLE_PATH)
        first_id = races[0].race_id
        r_entries = entries_map[first_id]

        # baseline
        odds = [e.odds_win for e in r_entries if e.odds_win]
        mkt_probs = market_probs_from_odds(odds)
        mkt_map = {e.horse_number: p for e, p in zip(r_entries, mkt_probs)}
        baseline_preds = generate_baseline_predictions(r_entries, mkt_map)
        baseline_max_edge = max(abs(p.edge_win) for p in baseline_preds)

        # core scoring (no features)
        core_preds = generate_core_predictions(r_entries)
        core_max_edge = max(abs(p.edge_win) for p in core_preds)

        # Core scoring の edge は baseline より桁違いに小さい
        assert core_max_edge < baseline_max_edge * 0.1

    def test_empty_entries(self):
        preds = generate_core_predictions([])
        assert preds == []
