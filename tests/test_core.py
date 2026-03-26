"""Core baseline / market のテスト"""

import pytest

from kawasaki_keiba.core.baseline import (
    compare_baseline_variants,
    generate_baseline_predictions,
    generate_odds_rank_baseline_predictions,
    generate_shrinkage_baseline_predictions,
    popularity_place_prob,
    popularity_win_prob,
)
from kawasaki_keiba.core.market import (
    market_probs_from_odds,
    normalize_probs,
    odds_to_implied_prob,
    overround,
)
from kawasaki_keiba.schemas.race import HorseEntry

# ---------------------------------------------------------------------------
# Popularity baseline
# ---------------------------------------------------------------------------

class TestPopularityWinProb:
    def test_rank1_highest(self):
        p1 = popularity_win_prob(1, 10)
        p2 = popularity_win_prob(2, 10)
        assert p1 > p2

    def test_probabilities_sum_to_one(self):
        n = 12
        total = sum(popularity_win_prob(r, n) for r in range(1, n + 1))
        assert total == pytest.approx(1.0)

    def test_single_runner(self):
        assert popularity_win_prob(1, 1) == pytest.approx(1.0)

    def test_invalid_popularity(self):
        with pytest.raises(ValueError, match="popularity"):
            popularity_win_prob(0, 10)

    def test_popularity_exceeds_runners(self):
        with pytest.raises(ValueError, match="popularity.*num_runners"):
            popularity_win_prob(11, 10)


class TestPopularityPlaceProb:
    def test_rank1_high_place_prob(self):
        pp = popularity_place_prob(1, 12)
        assert pp > 0.5

    def test_place_prob_capped_at_one(self):
        pp = popularity_place_prob(1, 3)
        assert pp <= 1.0

    def test_small_field_adjusts_places(self):
        # 4頭以下は places=2 に調整される
        pp_small = popularity_place_prob(1, 4, places=3)
        # 4頭の1番人気は高い複勝率になるはず
        assert pp_small > 0.5


class TestGenerateBaseline:
    def _make_entries(self, n: int, with_popularity: bool = True) -> list[HorseEntry]:
        return [
            HorseEntry(
                race_id="20260301_KW_07",
                horse_id=f"H{i:03d}",
                horse_name=f"Horse{i}",
                post_position=i,
                horse_number=i,
                jockey_id=f"J{i:03d}",
                jockey_name=f"Jockey{i}",
                trainer_id=f"T{i:03d}",
                weight_carried=56.0,
                popularity=i if with_popularity else None,
            )
            for i in range(1, n + 1)
        ]

    def test_returns_correct_count(self):
        entries = self._make_entries(8)
        preds = generate_baseline_predictions(entries)
        assert len(preds) == 8

    def test_rank1_has_highest_win_prob(self):
        entries = self._make_entries(10)
        preds = generate_baseline_predictions(entries)
        by_horse = {p.horse_number: p for p in preds}
        assert by_horse[1].win_prob > by_horse[10].win_prob

    def test_edge_is_zero_without_market(self):
        entries = self._make_entries(6)
        preds = generate_baseline_predictions(entries)
        for p in preds:
            assert p.edge_win == pytest.approx(0.0)

    def test_with_market_probs(self):
        entries = self._make_entries(4)
        market = {1: 0.4, 2: 0.3, 3: 0.2, 4: 0.1}
        preds = generate_baseline_predictions(entries, market_probs=market)
        by_horse = {p.horse_number: p for p in preds}
        # baseline の win_prob と market_prob が異なるので edge != 0
        assert by_horse[1].market_win_prob == 0.4

    def test_no_popularity_falls_back_to_horse_number(self):
        entries = self._make_entries(5, with_popularity=False)
        preds = generate_baseline_predictions(entries)
        assert len(preds) == 5

    def test_empty_entries(self):
        assert generate_baseline_predictions([]) == []


# ---------------------------------------------------------------------------
# Odds-rank baseline (1 alternative for inverse-FLB comparison)
# ---------------------------------------------------------------------------


class TestOddsRankBaseline:
    def test_lowest_odds_gets_highest_win_prob(self):
        entries = [
            HorseEntry(
                race_id="T",
                horse_id="H1",
                horse_name="A",
                post_position=1,
                horse_number=1,
                jockey_id="J",
                jockey_name="J",
                trainer_id="T",
                weight_carried=55.0,
                popularity=2,
                odds_win=8.0,
            ),
            HorseEntry(
                race_id="T",
                horse_id="H2",
                horse_name="B",
                post_position=2,
                horse_number=2,
                jockey_id="J",
                jockey_name="J",
                trainer_id="T",
                weight_carried=55.0,
                popularity=1,
                odds_win=2.0,
            ),
        ]
        preds = generate_odds_rank_baseline_predictions(entries)
        by_n = {p.horse_number: p for p in preds}
        assert by_n[2].win_prob > by_n[1].win_prob

    def test_matches_popularity_when_order_agrees(self):
        entries = [
            HorseEntry(
                race_id="T",
                horse_id="H1",
                horse_name="A",
                post_position=1,
                horse_number=1,
                jockey_id="J",
                jockey_name="J",
                trainer_id="T",
                weight_carried=55.0,
                popularity=1,
                odds_win=2.0,
            ),
            HorseEntry(
                race_id="T",
                horse_id="H2",
                horse_name="B",
                post_position=2,
                horse_number=2,
                jockey_id="J",
                jockey_name="J",
                trainer_id="T",
                weight_carried=55.0,
                popularity=2,
                odds_win=5.0,
            ),
        ]
        mkt = {1: 0.6, 2: 0.4}
        pop_p = generate_baseline_predictions(entries, mkt)
        odds_p = generate_odds_rank_baseline_predictions(entries, mkt)
        for a, b in zip(
            sorted(pop_p, key=lambda x: x.horse_number),
            sorted(odds_p, key=lambda x: x.horse_number),
            strict=True,
        ):
            assert a.win_prob == pytest.approx(b.win_prob)
            assert a.edge_win == pytest.approx(b.edge_win)

    def test_inverse_flb_scenario_odds_rank_reduces_max_abs_edge(self):
        """人気1位とオッズ1番手が食い違うとき、オッズ順の方が max|edge_win| が小さくなりやすい。"""
        entries = [
            HorseEntry(
                race_id="T",
                horse_id="Ha",
                horse_name="A",
                post_position=1,
                horse_number=1,
                jockey_id="J",
                jockey_name="J",
                trainer_id="T",
                weight_carried=55.0,
                popularity=1,
                odds_win=6.0,
            ),
            HorseEntry(
                race_id="T",
                horse_id="Hb",
                horse_name="B",
                post_position=2,
                horse_number=2,
                jockey_id="J",
                jockey_name="J",
                trainer_id="T",
                weight_carried=55.0,
                popularity=2,
                odds_win=2.5,
            ),
            HorseEntry(
                race_id="T",
                horse_id="Hc",
                horse_name="C",
                post_position=3,
                horse_number=3,
                jockey_id="J",
                jockey_name="J",
                trainer_id="T",
                weight_carried=55.0,
                popularity=3,
                odds_win=8.0,
            ),
            HorseEntry(
                race_id="T",
                horse_id="Hd",
                horse_name="D",
                post_position=4,
                horse_number=4,
                jockey_id="J",
                jockey_name="J",
                trainer_id="T",
                weight_carried=55.0,
                popularity=4,
                odds_win=12.0,
            ),
        ]
        odds_list = [float(e.odds_win) for e in entries]
        mkt_list = market_probs_from_odds(odds_list)
        market = {e.horse_number: p for e, p in zip(entries, mkt_list, strict=True)}
        cmp = compare_baseline_variants(entries, market)
        assert cmp["popularity_max_abs_edge"] > cmp["odds_rank_max_abs_edge"]


# ---------------------------------------------------------------------------
# Shrinkage baseline (market + uniform blend)
# ---------------------------------------------------------------------------


class TestShrinkageBaseline:
    def test_win_probs_sum_to_one(self):
        entries = [
            HorseEntry(
                race_id="T",
                horse_id="H1",
                horse_name="A",
                post_position=1,
                horse_number=1,
                jockey_id="J",
                jockey_name="J",
                trainer_id="T",
                weight_carried=55.0,
                popularity=1,
                odds_win=2.0,
            ),
            HorseEntry(
                race_id="T",
                horse_id="H2",
                horse_name="B",
                post_position=2,
                horse_number=2,
                jockey_id="J",
                jockey_name="J",
                trainer_id="T",
                weight_carried=55.0,
                popularity=2,
                odds_win=4.0,
            ),
        ]
        mkt_list = market_probs_from_odds([2.0, 4.0])
        mkt = {e.horse_number: p for e, p in zip(entries, mkt_list, strict=True)}
        preds = generate_shrinkage_baseline_predictions(entries, mkt, alpha=0.8)
        assert sum(p.win_prob for p in preds) == pytest.approx(1.0)

    def test_alpha_one_matches_market_edges_zero(self):
        entries = [
            HorseEntry(
                race_id="T",
                horse_id="H1",
                horse_name="A",
                post_position=1,
                horse_number=1,
                jockey_id="J",
                jockey_name="J",
                trainer_id="T",
                weight_carried=55.0,
                popularity=1,
                odds_win=3.0,
            ),
            HorseEntry(
                race_id="T",
                horse_id="H2",
                horse_name="B",
                post_position=2,
                horse_number=2,
                jockey_id="J",
                jockey_name="J",
                trainer_id="T",
                weight_carried=55.0,
                popularity=2,
                odds_win=3.0,
            ),
        ]
        mkt = {1: 0.5, 2: 0.5}
        preds = generate_shrinkage_baseline_predictions(entries, mkt, alpha=1.0)
        for p in preds:
            assert p.edge_win == pytest.approx(0.0)

    def test_invalid_alpha(self):
        entries = [
            HorseEntry(
                race_id="T",
                horse_id="H1",
                horse_name="A",
                post_position=1,
                horse_number=1,
                jockey_id="J",
                jockey_name="J",
                trainer_id="T",
                weight_carried=55.0,
                popularity=1,
                odds_win=2.0,
            ),
        ]
        with pytest.raises(ValueError, match="alpha"):
            generate_shrinkage_baseline_predictions(entries, {1: 1.0}, alpha=1.5)


class TestCompareBaselineVariants:
    def test_empty_entries(self):
        row = compare_baseline_variants([], {})
        assert row["n_runners"] == 0
        assert row["shrinkage_alpha"] == pytest.approx(0.8)

    def test_three_keys_present(self):
        entries = [
            HorseEntry(
                race_id="T",
                horse_id="H1",
                horse_name="A",
                post_position=1,
                horse_number=1,
                jockey_id="J",
                jockey_name="J",
                trainer_id="T",
                weight_carried=55.0,
                popularity=1,
                odds_win=2.0,
            ),
            HorseEntry(
                race_id="T",
                horse_id="H2",
                horse_name="B",
                post_position=2,
                horse_number=2,
                jockey_id="J",
                jockey_name="J",
                trainer_id="T",
                weight_carried=55.0,
                popularity=2,
                odds_win=4.0,
            ),
        ]
        mkt_list = market_probs_from_odds([2.0, 4.0])
        mkt = {e.horse_number: p for e, p in zip(entries, mkt_list, strict=True)}
        result = compare_baseline_variants(entries, mkt, shrinkage_alpha=0.8)
        assert result["shrinkage_alpha"] == pytest.approx(0.8)
        assert "popularity_max_abs_edge" in result
        assert "odds_rank_max_abs_edge" in result
        assert "shrinkage_max_abs_edge" in result

    def test_sample_races_ten_way_compare(self):
        """実データ10レース: 3案の max|edge| を合計して比較しやすくする。"""
        from pathlib import Path

        from kawasaki_keiba.data.loader import load_entries, load_races

        p = Path(__file__).resolve().parent.parent / "data" / "raw" / "sample_races.json"
        if not p.is_file():
            pytest.skip("sample_races.json missing")
        races = load_races(p)
        all_e = load_entries(p)
        assert len(races) >= 10

        pop_sum_max = 0.0
        odds_sum_max = 0.0
        shrink_sum_max = 0.0
        for race in races:
            ent = all_e[race.race_id]
            odds_f = [float(e.odds_win) for e in ent if e.odds_win is not None]
            if len(odds_f) != len(ent):
                pytest.fail("sample entries need odds for all runners")
            probs = market_probs_from_odds(odds_f)
            mkt = {e.horse_number: pr for e, pr in zip(ent, probs, strict=True)}
            row = compare_baseline_variants(ent, mkt)
            assert row["race_id"] == race.race_id
            assert row["n_runners"] == len(ent)
            assert row["shrinkage_alpha"] == pytest.approx(0.8)
            pop_sum_max += float(row["popularity_max_abs_edge"])
            odds_sum_max += float(row["odds_rank_max_abs_edge"])
            shrink_sum_max += float(row["shrinkage_max_abs_edge"])

        # サンプルではオッズ順の max|edge| の合計が人気順以下（同一調和級数なら一致しうる）
        assert odds_sum_max <= pop_sum_max + 1e-9
        # Shrinkage は市場へ滑らかに寄せるため、調和級数2案より max|edge| 合計が小さい
        assert shrink_sum_max < pop_sum_max - 1e-6


# ---------------------------------------------------------------------------
# Market
# ---------------------------------------------------------------------------

class TestOddsToImpliedProb:
    def test_even_odds(self):
        assert odds_to_implied_prob(2.0) == pytest.approx(0.5)

    def test_favorite(self):
        assert odds_to_implied_prob(1.5) == pytest.approx(1.0 / 1.5)

    def test_longshot(self):
        assert odds_to_implied_prob(100.0) == pytest.approx(0.01)

    def test_invalid_odds(self):
        with pytest.raises(ValueError, match="positive"):
            odds_to_implied_prob(0.0)
        with pytest.raises(ValueError, match="positive"):
            odds_to_implied_prob(-1.0)


class TestNormalizeProbs:
    def test_already_normalized(self):
        result = normalize_probs([0.5, 0.3, 0.2])
        assert sum(result) == pytest.approx(1.0)

    def test_overround_removed(self):
        result = normalize_probs([0.6, 0.4, 0.3])  # sum = 1.3
        assert sum(result) == pytest.approx(1.0)
        assert result[0] > result[1] > result[2]


class TestMarketProbsFromOdds:
    def test_basic(self):
        probs = market_probs_from_odds([2.0, 4.0, 8.0])
        assert sum(probs) == pytest.approx(1.0)
        assert probs[0] > probs[1] > probs[2]

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            market_probs_from_odds([])


class TestOverround:
    def test_typical_overround(self):
        # 2倍, 4倍, 8倍 → 0.5 + 0.25 + 0.125 = 0.875 (実際はアンダーラウンド)
        assert overround([2.0, 4.0, 8.0]) == pytest.approx(0.875)

    def test_fair_book(self):
        # 完全な fair book なら 1.0
        assert overround([2.0, 2.0]) == pytest.approx(1.0)
