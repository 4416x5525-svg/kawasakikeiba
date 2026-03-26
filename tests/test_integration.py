"""Integration スコア正規化・統合判定のテスト"""


import pytest

from kawasaki_keiba.gate.reason_codes import NoBetReasonCode
from kawasaki_keiba.integration.decision import (
    RawSubsystemScores,
    build_integration_decision,
)
from kawasaki_keiba.integration.score_normalization import (
    normalize_core_score,
    rescale_to_band,
)


class TestRescaleToBand:
    def test_midpoint(self):
        assert rescale_to_band(0.0, src_low=-1.0, src_high=1.0) == 0.0

    def test_low_boundary(self):
        assert rescale_to_band(-1.0, src_low=-1.0, src_high=1.0) == -2.0

    def test_high_boundary(self):
        assert rescale_to_band(1.0, src_low=-1.0, src_high=1.0) == 2.0

    def test_clipping_above(self):
        assert rescale_to_band(5.0, src_low=-1.0, src_high=1.0) == 2.0

    def test_clipping_below(self):
        assert rescale_to_band(-5.0, src_low=-1.0, src_high=1.0) == -2.0

    def test_nan_raises(self):
        with pytest.raises(ValueError, match="finite"):
            rescale_to_band(float("nan"), src_low=-1.0, src_high=1.0)

    def test_inf_raises(self):
        with pytest.raises(ValueError, match="finite"):
            rescale_to_band(float("inf"), src_low=-1.0, src_high=1.0)

    def test_invalid_src_range(self):
        with pytest.raises(ValueError, match="src_high"):
            rescale_to_band(0.0, src_low=1.0, src_high=-1.0)


class TestNormalizeCoreScore:
    def test_default_range(self):
        assert normalize_core_score(0.5) == pytest.approx(1.0)
        assert normalize_core_score(-0.5) == pytest.approx(-1.0)


class TestBuildIntegrationDecision:
    def test_core_only_positive(self):
        raw = RawSubsystemScores(core=0.5)
        dec = build_integration_decision(raw)
        assert dec.gate.bet
        assert "core" in dec.normalized

    def test_core_only_negative(self):
        raw = RawSubsystemScores(core=-1.0)
        dec = build_integration_decision(raw)
        assert not dec.gate.bet

    def test_all_subsystems(self):
        raw = RawSubsystemScores(core=0.5, race=0.3, paddock=0.2, warmup=0.1)
        dec = build_integration_decision(raw)
        assert dec.gate.bet
        assert len(dec.normalized) == 4

    def test_no_core_required(self):
        raw = RawSubsystemScores(core=None)
        dec = build_integration_decision(raw, require_core=True)
        assert not dec.gate.bet
        assert NoBetReasonCode.MISSING_REQUIRED_SCORE in dec.gate.no_bet_reasons

    def test_veto_flags_default_false(self):
        raw = RawSubsystemScores(core=0.5)
        dec = build_integration_decision(raw)
        assert not dec.race_video_veto
        assert not dec.paddock_veto
        assert not dec.warmup_veto
