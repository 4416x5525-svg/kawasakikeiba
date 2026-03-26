"""Wind モジュールのテスト"""

from kawasaki_keiba.wind.estimate import WindEstimate, estimate_wind_impact


class TestWindEstimate:
    def test_north_wind_is_headwind(self):
        """北風(北から吹く)= 直線向かい風（川崎の直線は北向き）→ 先行有利仮説。"""
        est = estimate_wind_impact(
            wind_direction_deg=0.0,  # 北風（北から吹く → 南へ向かう）
            wind_speed_mps=8.0,
        )
        # 北風 → ゴール方向に逆らう → 向かい風 → 先行有利 → 負のスコア
        assert est.headwind_component > 0
        assert est.wind_score < 0
        assert "向かい風" in est.short_reason

    def test_south_wind_is_tailwind(self):
        """南風(南から吹く)= 直線追い風 → 差し有利仮説。"""
        est = estimate_wind_impact(
            wind_direction_deg=180.0,  # 南風（南から吹く → 北へ向かう）
            wind_speed_mps=8.0,
        )
        assert est.tailwind_component > 0
        assert est.wind_score > 0
        assert "追い風" in est.short_reason

    def test_calm_wind(self):
        """微風は影響なし。"""
        est = estimate_wind_impact(
            wind_direction_deg=90.0,
            wind_speed_mps=1.0,
        )
        assert est.confidence <= 0.1
        assert abs(est.wind_score) < 0.5

    def test_crosswind(self):
        """横風は直線成分が比較的小さい。"""
        est = estimate_wind_impact(
            wind_direction_deg=90.0,  # 東風（直線に対して横）
            wind_speed_mps=10.0,
        )
        # 完全横風ではないが（直線が20度傾いているため）成分は小さめ
        assert abs(est.tailwind_component) < 8.0
        assert est.confidence <= 0.3

    def test_confidence_always_low(self):
        """Wind の confidence は常に 0.3 以下。"""
        est = estimate_wind_impact(
            wind_direction_deg=0.0,
            wind_speed_mps=20.0,
        )
        assert est.confidence <= 0.3

    def test_score_bounded(self):
        """スコアは [-2, 2] に収まる。"""
        for deg in range(0, 360, 45):
            for speed in [0, 5, 10, 20, 50]:
                est = estimate_wind_impact(float(deg), float(speed))
                assert -2.0 <= est.wind_score <= 2.0

    def test_negative_speed_handled(self):
        """負の風速は 0 に補正。"""
        est = estimate_wind_impact(0.0, -5.0)
        assert est.wind_speed_mps == 0.0

    def test_to_dict(self):
        est = estimate_wind_impact(45.0, 6.0)
        d = est.to_dict()
        assert "wind_score" in d
        assert "confidence" in d
        assert "impact_hypothesis" in d
        assert "short_reason" in d

    def test_distance_affects_score(self):
        """短距離ほど影響が大きい。"""
        short = estimate_wind_impact(0.0, 10.0, distance=900)
        long = estimate_wind_impact(0.0, 10.0, distance=2100)
        assert abs(short.wind_score) > abs(long.wind_score)
