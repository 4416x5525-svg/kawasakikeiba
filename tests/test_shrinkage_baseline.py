"""Shrinkage baseline のテスト + 3案比較"""

from pathlib import Path

import pytest

from kawasaki_keiba.core.baseline import (
    compare_baseline_variants,
    generate_baseline_predictions,
    generate_odds_rank_baseline_predictions,
    generate_shrinkage_baseline_predictions,
)
from kawasaki_keiba.core.market import market_probs_from_odds
from kawasaki_keiba.data.loader import load_entries, load_races

SAMPLE_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "sample_races.json"


def _first_race_data():
    races = load_races(SAMPLE_PATH)
    entries_map = load_entries(SAMPLE_PATH)
    first_id = races[0].race_id
    r_entries = entries_map[first_id]
    odds = [e.odds_win for e in r_entries if e.odds_win]
    mkt_probs = market_probs_from_odds(odds)
    mkt_map = {e.horse_number: p for e, p in zip(r_entries, mkt_probs)}
    return r_entries, mkt_map


class TestShrinkageBaseline:
    def test_alpha_one_equals_market(self):
        """α=1.0 なら市場確率そのまま。edge=0。"""
        entries, mkt_map = _first_race_data()
        preds = generate_shrinkage_baseline_predictions(entries, mkt_map, alpha=1.0)
        for p in preds:
            assert abs(p.edge_win) < 0.0001

    def test_alpha_zero_equals_uniform(self):
        """α=0.0 なら均等確率。"""
        entries, mkt_map = _first_race_data()
        preds = generate_shrinkage_baseline_predictions(entries, mkt_map, alpha=0.0)
        uniform = 1.0 / len(entries)
        for p in preds:
            assert abs(p.win_prob - uniform) < 0.0001

    def test_alpha_08_moderate_edge(self):
        """α=0.8 なら微小な edge が出る。"""
        entries, mkt_map = _first_race_data()
        preds = generate_shrinkage_baseline_predictions(entries, mkt_map, alpha=0.8)
        max_edge = max(abs(p.edge_win) for p in preds)
        # edge はゼロではないが、popularity baseline より遥かに小さい
        assert max_edge > 0.0001
        assert max_edge < 0.05

    def test_favorite_gets_negative_edge(self):
        """α<1 なら人気馬の edge は負（市場が過大評価していると仮定）。"""
        entries, mkt_map = _first_race_data()
        preds = generate_shrinkage_baseline_predictions(entries, mkt_map, alpha=0.8)
        # 最も市場確率が高い馬
        fav = max(preds, key=lambda p: p.market_win_prob)
        assert fav.edge_win < 0

    def test_longshot_gets_positive_edge(self):
        """α<1 なら穴馬の edge は正（市場が過小評価していると仮定）。"""
        entries, mkt_map = _first_race_data()
        preds = generate_shrinkage_baseline_predictions(entries, mkt_map, alpha=0.8)
        # 最も市場確率が低い馬
        ls = min(preds, key=lambda p: p.market_win_prob)
        assert ls.edge_win > 0

    def test_probs_sum_to_one(self):
        """win_prob の合計は 1.0 に近い。"""
        entries, mkt_map = _first_race_data()
        preds = generate_shrinkage_baseline_predictions(entries, mkt_map, alpha=0.8)
        total = sum(p.win_prob for p in preds)
        assert total == pytest.approx(1.0, abs=0.01)

    def test_invalid_alpha(self):
        entries, mkt_map = _first_race_data()
        with pytest.raises(ValueError, match="alpha"):
            generate_shrinkage_baseline_predictions(entries, mkt_map, alpha=1.5)

    def test_empty_entries(self):
        preds = generate_shrinkage_baseline_predictions([], {})
        assert preds == []

    def test_rank_score_ordering(self):
        """rank_score は win_prob 降順で 1.0 → 0.0。"""
        entries, mkt_map = _first_race_data()
        preds = generate_shrinkage_baseline_predictions(entries, mkt_map, alpha=0.8)
        sorted_preds = sorted(preds, key=lambda p: p.rank_score, reverse=True)
        for i in range(len(sorted_preds) - 1):
            assert sorted_preds[i].win_prob >= sorted_preds[i + 1].win_prob - 0.001


class TestCompareVariants:
    def test_three_variants_returned(self):
        """3案の比較結果が全て含まれる。"""
        entries, mkt_map = _first_race_data()
        result = compare_baseline_variants(entries, mkt_map)
        assert "popularity_max_abs_edge" in result
        assert "odds_rank_max_abs_edge" in result
        assert "shrinkage_max_abs_edge" in result

    def test_shrinkage_between_popularity_and_market(self):
        """Shrinkage の |edge| は popularity より小さく、0 より大きい。"""
        entries, mkt_map = _first_race_data()
        result = compare_baseline_variants(entries, mkt_map, shrinkage_alpha=0.8)
        pop = result["popularity_max_abs_edge"]
        shrink = result["shrinkage_max_abs_edge"]
        # shrinkage は popularity より edge が小さい
        assert shrink < pop
        # shrinkage は 0 より大きい（α<1 なので信号がある）
        assert shrink > 0

    def test_edge_ordering(self):
        """max|edge| の大小関係: popularity > odds_rank >= shrinkage > 0。"""
        entries, mkt_map = _first_race_data()
        result = compare_baseline_variants(entries, mkt_map, shrinkage_alpha=0.8)
        pop = result["popularity_max_abs_edge"]
        odds = result["odds_rank_max_abs_edge"]
        shrink = result["shrinkage_max_abs_edge"]
        # popularity が最大
        assert pop >= odds
        assert pop >= shrink
        # shrinkage は正
        assert shrink > 0
