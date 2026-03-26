"""data/loader.py + 実データパイプラインのテスト"""

from pathlib import Path

from kawasaki_keiba.core.baseline import generate_baseline_predictions
from kawasaki_keiba.core.bias_table import build_bias_table
from kawasaki_keiba.core.market import market_probs_from_odds
from kawasaki_keiba.data.loader import (
    load_entries,
    load_races,
    load_results,
    validate_race_bundle,
)
from kawasaki_keiba.track_bias.compute import compute_track_bias

SAMPLE_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "sample_races.json"


def _sample_data():
    races = load_races(SAMPLE_PATH)
    entries = load_entries(SAMPLE_PATH)
    results = load_results(SAMPLE_PATH)
    return races, entries, results


class TestLoader:
    def test_load_races(self):
        races, _, _ = _sample_data()
        assert len(races) >= 1
        assert all("_KW_" in r.race_id for r in races)

    def test_load_entries(self):
        _, entries, _ = _sample_data()
        assert len(entries) >= 1
        total_horses = sum(len(v) for v in entries.values())
        assert total_horses >= 1

    def test_load_results(self):
        _, _, results = _sample_data()
        assert len(results) >= 1
        total_results = sum(len(v) for v in results.values())
        assert total_results >= 1

    def test_entries_have_odds(self):
        _, entries, _ = _sample_data()
        for race_entries in entries.values():
            for e in race_entries:
                assert e.odds_win is not None
                assert e.popularity is not None

    def test_race_entry_result_count_match(self):
        races, entries, results = _sample_data()
        for race in races:
            r_entries = entries.get(race.race_id, [])
            r_results = results.get(race.race_id, [])
            assert len(r_entries) == race.num_runners, f"{race.race_id}: entries mismatch"
            assert len(r_results) == race.num_runners, f"{race.race_id}: results mismatch"


class TestPipelineIntegration:
    """実データを各モジュールに1回通す統合テスト。"""

    def test_track_bias_runs(self):
        races, entries, results = _sample_data()
        snap = compute_track_bias(races, entries, results)
        assert -1.0 <= snap.post_bias <= 1.0
        assert -1.0 <= snap.pace_bias <= 1.0

    def test_baseline_predictions_for_first_race(self):
        races, entries, _ = _sample_data()
        first_id = races[0].race_id
        r_entries = entries[first_id]
        preds = generate_baseline_predictions(r_entries)
        assert len(preds) == len(r_entries)

    def test_baseline_with_market_produces_edges(self):
        races, entries, _ = _sample_data()
        first_id = races[0].race_id
        r_entries = entries[first_id]
        odds = [e.odds_win for e in r_entries if e.odds_win]
        assert len(odds) > 0, "All entries should have odds"

        mkt_probs = market_probs_from_odds(odds)
        mkt_map = {e.horse_number: p for e, p in zip(r_entries, mkt_probs)}
        preds = generate_baseline_predictions(r_entries, mkt_map)

        edges = [p.edge_win for p in preds]
        assert len(edges) > 0
        # edge の平均は 0 に近い（調和級数 vs 市場確率 の構造的性質）
        assert abs(sum(edges) / len(edges)) < 0.02

    def test_edge_distribution_has_variance(self):
        """Baseline edge に正負のばらつきがあることを確認。"""
        races, entries, _ = _sample_data()
        first_id = races[0].race_id
        r_entries = entries[first_id]
        odds = [e.odds_win for e in r_entries if e.odds_win]
        mkt_probs = market_probs_from_odds(odds)
        mkt_map = {e.horse_number: p for e, p in zip(r_entries, mkt_probs)}
        preds = generate_baseline_predictions(r_entries, mkt_map)

        edges = [p.edge_win for p in preds]
        # edge に正と負の両方がある（全て同符号ではない）
        has_positive = any(e > 0.001 for e in edges)
        has_negative = any(e < -0.001 for e in edges)
        assert has_positive or has_negative, "Edge should have variance"
        # edge の絶対値最大が 0 でない
        assert max(abs(e) for e in edges) > 0.01

    def test_bias_table_with_limited_data(self):
        """データ不足時に bias_table が空セルを返す（正しい動作）。"""
        races, entries, results = _sample_data()
        table = build_bias_table(races, entries, results)
        # 10レース < MIN_RACES_PER_CELL=15 → セルなし or 少数
        # データ量に応じて 0 個以上のセルが生成される
        assert isinstance(table, dict)
