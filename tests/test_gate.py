"""Gate ルール・理由コードのテスト"""

from kawasaki_keiba.gate.reason_codes import BetReasonCode, NoBetReasonCode
from kawasaki_keiba.gate.rules import (
    GateRuleInput,
    evaluate_gate_minimal,
)


class TestReasonCodes:
    def test_no_bet_codes_are_strings(self):
        assert str(NoBetReasonCode.WEAK_CORE) == "weak_core"
        assert str(NoBetReasonCode.VIDEO_VETO) == "video_veto"

    def test_bet_codes_are_strings(self):
        assert str(BetReasonCode.RULE_PASS) == "rule_pass"


class TestGateMinimal:
    def test_video_veto_forces_no_bet(self):
        inp = GateRuleInput(core=1.0, race_video_veto=True)
        result = evaluate_gate_minimal(inp)
        assert not result.bet
        assert NoBetReasonCode.VIDEO_VETO in result.no_bet_reasons

    def test_paddock_veto_forces_no_bet(self):
        inp = GateRuleInput(core=1.0, paddock_veto=True)
        result = evaluate_gate_minimal(inp)
        assert not result.bet
        assert NoBetReasonCode.PADDOCK_VETO in result.no_bet_reasons

    def test_warmup_veto_forces_no_bet(self):
        inp = GateRuleInput(core=1.0, warmup_veto=True)
        result = evaluate_gate_minimal(inp)
        assert not result.bet
        assert NoBetReasonCode.WARMUP_VETO in result.no_bet_reasons

    def test_missing_core_when_required(self):
        inp = GateRuleInput(core=None, require_core=True)
        result = evaluate_gate_minimal(inp)
        assert not result.bet
        assert NoBetReasonCode.MISSING_REQUIRED_SCORE in result.no_bet_reasons

    def test_missing_core_not_required(self):
        inp = GateRuleInput(core=None, race=0.5, require_core=False)
        result = evaluate_gate_minimal(inp)
        assert result.bet

    def test_weak_core_no_bet(self):
        inp = GateRuleInput(core=-1.5)
        result = evaluate_gate_minimal(inp)
        assert not result.bet
        assert NoBetReasonCode.WEAK_CORE in result.no_bet_reasons

    def test_positive_core_bet(self):
        inp = GateRuleInput(core=0.5)
        result = evaluate_gate_minimal(inp)
        assert result.bet
        assert BetReasonCode.RULE_PASS in result.bet_reasons
        assert BetReasonCode.CORE_SUPPORT in result.bet_reasons

    def test_consensus_support(self):
        inp = GateRuleInput(core=0.5, race=0.1, paddock=0.2, warmup=0.3)
        result = evaluate_gate_minimal(inp)
        assert result.bet
        assert BetReasonCode.CONSENSUS_SUPPORT in result.bet_reasons

    def test_no_signal_at_all(self):
        inp = GateRuleInput(core=None, require_core=False)
        result = evaluate_gate_minimal(inp)
        assert not result.bet
        assert NoBetReasonCode.INSUFFICIENT_SIGNAL in result.no_bet_reasons

    def test_weak_aggregate_no_bet(self):
        inp = GateRuleInput(core=-0.5, race=-0.8)
        result = evaluate_gate_minimal(inp)
        assert not result.bet
        assert NoBetReasonCode.WEAK_AGGREGATE in result.no_bet_reasons
