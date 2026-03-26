"""Monitoring logger / roi_tracker のテスト"""

from datetime import datetime
from pathlib import Path

import pytest

from kawasaki_keiba.monitoring.logger import JudgmentLogger
from kawasaki_keiba.monitoring.roi_tracker import (
    build_monitoring_snapshot,
    calculate_roi,
)
from kawasaki_keiba.schemas.judgment_log import JudgmentLog


def _make_log(
    race_id: str,
    *,
    bet_placed: bool = True,
    bet_amount: int = 100,
    payout: int = 0,
) -> JudgmentLog:
    return JudgmentLog(
        race_id=race_id,
        timestamp=datetime.now(),
        core_predictions=[],
        gate_decision="bet" if bet_placed else "no_bet",
        gate_confidence=0.7,
        bet_placed=bet_placed,
        bet_amount=bet_amount if bet_placed else None,
        payout=payout if bet_placed else None,
        profit=(payout - bet_amount) if bet_placed else None,
    )


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

class TestJudgmentLogger:
    def test_save_and_load(self, tmp_path: Path):
        db = tmp_path / "test.db"
        logger = JudgmentLogger(db)
        log = _make_log("20260301_KW_07", bet_amount=100, payout=350)
        logger.save(log)

        loaded = logger.load("20260301_KW_07")
        assert loaded is not None
        assert loaded.race_id == "20260301_KW_07"
        assert loaded.payout == 350

    def test_load_nonexistent(self, tmp_path: Path):
        db = tmp_path / "test.db"
        logger = JudgmentLogger(db)
        assert logger.load("nonexistent") is None

    def test_overwrite_on_save(self, tmp_path: Path):
        db = tmp_path / "test.db"
        logger = JudgmentLogger(db)
        logger.save(_make_log("20260301_KW_07", payout=100))
        logger.save(_make_log("20260301_KW_07", payout=500))

        loaded = logger.load("20260301_KW_07")
        assert loaded is not None
        assert loaded.payout == 500

    def test_list_recent(self, tmp_path: Path):
        db = tmp_path / "test.db"
        logger = JudgmentLogger(db)
        for i in range(1, 6):
            logger.save(_make_log(f"20260301_KW_{i:02d}"))

        recent = logger.list_recent(3)
        assert len(recent) == 3

    def test_count(self, tmp_path: Path):
        db = tmp_path / "test.db"
        logger = JudgmentLogger(db)
        assert logger.count() == 0
        logger.save(_make_log("20260301_KW_01"))
        logger.save(_make_log("20260301_KW_02"))
        assert logger.count() == 2

    def test_list_all(self, tmp_path: Path):
        db = tmp_path / "test.db"
        logger = JudgmentLogger(db)
        logger.save(_make_log("20260301_KW_01"))
        logger.save(_make_log("20260301_KW_02"))
        all_logs = logger.list_all()
        assert len(all_logs) == 2

    def test_no_bet_log(self, tmp_path: Path):
        db = tmp_path / "test.db"
        logger = JudgmentLogger(db)
        log = _make_log("20260301_KW_07", bet_placed=False)
        logger.save(log)
        loaded = logger.load("20260301_KW_07")
        assert loaded is not None
        assert not loaded.bet_placed


# ---------------------------------------------------------------------------
# ROI Tracker
# ---------------------------------------------------------------------------

class TestCalculateRoi:
    def test_basic_roi(self):
        logs = [
            _make_log("R01", bet_amount=100, payout=300),
            _make_log("R02", bet_amount=100, payout=0),
            _make_log("R03", bet_amount=100, payout=0),
        ]
        invested, returned = calculate_roi(logs)
        assert invested == 300
        assert returned == 300

    def test_no_bets(self):
        logs = [_make_log("R01", bet_placed=False)]
        invested, returned = calculate_roi(logs)
        assert invested == 0
        assert returned == 0

    def test_mixed(self):
        logs = [
            _make_log("R01", bet_amount=100, payout=250),
            _make_log("R02", bet_placed=False),
            _make_log("R03", bet_amount=100, payout=0),
        ]
        invested, returned = calculate_roi(logs)
        assert invested == 200
        assert returned == 250


class TestBuildMonitoringSnapshot:
    def test_basic_snapshot(self):
        logs = [
            _make_log(f"R{i:02d}", bet_amount=100, payout=80)
            for i in range(1, 11)
        ]
        snapshot = build_monitoring_snapshot(logs)
        assert snapshot.total_bets == 10
        assert snapshot.total_no_bets == 0
        assert snapshot.total_invested == 1000
        assert snapshot.total_returned == 800
        assert snapshot.roi == pytest.approx(0.8)

    def test_recent_roi_requires_enough_data(self):
        logs = [_make_log(f"R{i:02d}") for i in range(1, 6)]
        snapshot = build_monitoring_snapshot(logs, recent_window=30)
        assert snapshot.recent_roi_30 is None  # 5件 < 30件

    def test_halt_triggered(self):
        # 30件すべて負け → ROI = 0
        logs = [
            _make_log(f"R{i:02d}", bet_amount=100, payout=0)
            for i in range(1, 31)
        ]
        snapshot = build_monitoring_snapshot(logs, recent_window=30, halt_threshold=0.7)
        assert snapshot.halt_active
        assert snapshot.halt_reason is not None

    def test_no_halt_when_profitable(self):
        logs = [
            _make_log(f"R{i:02d}", bet_amount=100, payout=120)
            for i in range(1, 31)
        ]
        snapshot = build_monitoring_snapshot(logs, recent_window=30)
        assert not snapshot.halt_active

    def test_empty_logs(self):
        snapshot = build_monitoring_snapshot([])
        assert snapshot.total_bets == 0
        assert snapshot.roi == 0.0
        assert not snapshot.halt_active
