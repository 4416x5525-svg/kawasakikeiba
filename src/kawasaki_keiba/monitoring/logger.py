"""JudgmentLog の SQLite 永続化。

1レース1レコード。JSON シリアライズで保存する。

サブシステム別の説明テキストはスキーマ拡張なしで integrated_scores に
record_type=subsystem_reasons_v1 の dict を1件足す约定で載せる。
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from kawasaki_keiba.integration.decision import IntegrationDecision
from kawasaki_keiba.schemas.judgment_log import JudgmentLog

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS judgment_logs (
    race_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""

_INSERT = """
INSERT OR REPLACE INTO judgment_logs (race_id, data, created_at)
VALUES (?, ?, ?)
"""

_SELECT_ONE = "SELECT data FROM judgment_logs WHERE race_id = ?"

_SELECT_RECENT = """
SELECT data FROM judgment_logs
ORDER BY created_at DESC
LIMIT ?
"""

_SELECT_ALL = "SELECT data FROM judgment_logs ORDER BY created_at ASC"

_SELECT_COUNT = "SELECT COUNT(*) FROM judgment_logs"

SUBSYSTEM_REASONS_RECORD_TYPE = "subsystem_reasons_v1"


def subsystem_reasons_payload(
    *,
    model_reason: str | None = None,
    race_reason: str | None = None,
    paddock_reason: str | None = None,
    warmup_reason: str | None = None,
    execution_reason: str | None = None,
) -> dict[str, Any]:
    """JudgmentLog.integrated_scores に格納する1レコード（キー固定）。"""
    return {
        "record_type": SUBSYSTEM_REASONS_RECORD_TYPE,
        "model_reason": model_reason,
        "race_reason": race_reason,
        "paddock_reason": paddock_reason,
        "warmup_reason": warmup_reason,
        "execution_reason": execution_reason,
    }


def judgment_log_with_subsystem_reasons(
    log: JudgmentLog,
    *,
    model_reason: str | None = None,
    race_reason: str | None = None,
    paddock_reason: str | None = None,
    warmup_reason: str | None = None,
    execution_reason: str | None = None,
    replace_existing: bool = True,
) -> JudgmentLog:
    """subsystem_reasons_v1 レコードを integrated_scores に付与（既存と置換可）。"""
    payload = subsystem_reasons_payload(
        model_reason=model_reason,
        race_reason=race_reason,
        paddock_reason=paddock_reason,
        warmup_reason=warmup_reason,
        execution_reason=execution_reason,
    )
    rows: list[dict[str, Any]] = list(log.integrated_scores or [])
    if replace_existing:
        rows = [r for r in rows if r.get("record_type") != SUBSYSTEM_REASONS_RECORD_TYPE]
    rows.append(payload)
    return log.model_copy(update={"integrated_scores": rows})


def subsystem_reasons_from_integration_decision(dec: IntegrationDecision) -> dict[str, Any]:
    """IntegrationDecision から subsystem_reasons_v1 用 dict を生成する。"""
    nb = ",".join(x.value for x in dec.gate.no_bet_reasons)
    br = ",".join(x.value for x in dec.gate.bet_reasons)
    execution = nb if nb else (br if br else "undetermined")
    return subsystem_reasons_payload(
        model_reason=_band_reason("core", dec.normalized),
        race_reason=_band_reason("race", dec.normalized),
        paddock_reason=_band_reason("paddock", dec.normalized),
        warmup_reason=_band_reason("warmup", dec.normalized),
        execution_reason=execution,
    )


def _band_reason(key: str, normalized: dict[str, float]) -> str | None:
    v = normalized.get(key)
    if v is None:
        return None
    return f"{key}={v:.4f}"


class JudgmentLogger:
    """JudgmentLog の永続化ハンドラ。"""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(_CREATE_TABLE)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def save(self, log: JudgmentLog) -> None:
        """JudgmentLog を保存する。同一 race_id は上書き。"""
        data = log.model_dump_json()
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(_INSERT, (log.race_id, data, now))

    def load(self, race_id: str) -> JudgmentLog | None:
        """race_id で JudgmentLog を取得する。"""
        with self._connect() as conn:
            row = conn.execute(_SELECT_ONE, (race_id,)).fetchone()
        if row is None:
            return None
        return JudgmentLog.model_validate_json(row[0])

    def list_recent(self, limit: int = 30) -> list[JudgmentLog]:
        """直近 N 件の JudgmentLog を取得する（新しい順）。"""
        with self._connect() as conn:
            rows = conn.execute(_SELECT_RECENT, (limit,)).fetchall()
        return [JudgmentLog.model_validate_json(row[0]) for row in rows]

    def list_all(self) -> list[JudgmentLog]:
        """全件取得（古い順）。"""
        with self._connect() as conn:
            rows = conn.execute(_SELECT_ALL).fetchall()
        return [JudgmentLog.model_validate_json(row[0]) for row in rows]

    def count(self) -> int:
        """レコード数を返す。"""
        with self._connect() as conn:
            row = conn.execute(_SELECT_COUNT).fetchone()
        return row[0] if row else 0
