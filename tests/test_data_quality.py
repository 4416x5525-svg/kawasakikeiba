"""データ品質チェックのテスト"""

from datetime import date

import pandas as pd
import pytest

from kawasaki_keiba.data_quality.leakage_guard import (
    TimeSeriesSplit,
    assert_no_forbidden_features,
    check_feature_leakage,
)
from kawasaki_keiba.data_quality.validators import validate_race_entries


class TestValidateRaceEntries:
    def test_valid_data(self):
        df = pd.DataFrame({
            "race_id": ["20260301_KW_07"] * 3,
            "horse_id": ["H1", "H2", "H3"],
            "horse_number": [1, 2, 3],
            "jockey_id": ["J1", "J2", "J3"],
            "weight_carried": [56.0, 55.0, 54.0],
            "distance": [1500, 1500, 1500],
            "race_date": [date(2026, 3, 1)] * 3,
        })
        result = validate_race_entries(df)
        assert result.is_valid

    def test_missing_columns(self):
        df = pd.DataFrame({"race_id": ["20260301_KW_07"]})
        result = validate_race_entries(df)
        assert not result.is_valid

    def test_invalid_distance(self):
        df = pd.DataFrame({
            "race_id": ["20260301_KW_07"],
            "horse_id": ["H1"],
            "horse_number": [1],
            "jockey_id": ["J1"],
            "weight_carried": [56.0],
            "distance": [3000],  # 川崎にない距離
            "race_date": [date(2026, 3, 1)],
        })
        result = validate_race_entries(df)
        assert any("距離範囲外" in w for w in result.warnings)


class TestTimeSeriesSplit:
    def test_valid_split(self):
        split = TimeSeriesSplit(
            train_start=date(2024, 1, 1),
            train_end=date(2024, 12, 31),
            val_start=date(2025, 1, 1),
            val_end=date(2025, 6, 30),
            test_start=date(2025, 7, 1),
            test_end=date(2025, 12, 31),
        )
        df = pd.DataFrame({
            "race_date": pd.date_range("2024-01-01", "2025-12-31", freq="D"),
        })
        train, val, test = split.split(df)
        assert len(train) > 0
        assert len(val) > 0
        assert len(test) > 0

    def test_invalid_order(self):
        with pytest.raises(ValueError, match="時系列分割の順序が不正"):
            TimeSeriesSplit(
                train_start=date(2025, 1, 1),
                train_end=date(2025, 12, 31),
                val_start=date(2024, 1, 1),  # train より前
                val_end=date(2024, 6, 30),
                test_start=date(2025, 7, 1),
                test_end=date(2025, 12, 31),
            )


class TestLeakageGuard:
    def test_forbidden_features(self):
        df = pd.DataFrame({"finish_position": [1, 2, 3], "some_feature": [0.1, 0.2, 0.3]})
        with pytest.raises(ValueError, match="予測時禁止列"):
            assert_no_forbidden_features(df)

    def test_clean_features(self):
        df = pd.DataFrame({"some_feature": [0.1, 0.2, 0.3]})
        assert_no_forbidden_features(df)  # should not raise

    def test_odds_warning(self):
        features = pd.DataFrame({"odds_win": [3.5, 10.0]})
        target = pd.DataFrame({"finish_position": [1, 2]})
        warnings = check_feature_leakage(features, target)
        assert any("odds_win" in w for w in warnings)
