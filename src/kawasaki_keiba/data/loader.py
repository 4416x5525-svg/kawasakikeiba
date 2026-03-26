"""sample_races.json 読込（bias 計算は行わない）。"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

from kawasaki_keiba.schemas.race import HorseEntry, RaceRecord, RaceResult


def _read_json(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        msg = "root must be a JSON object"
        raise ValueError(msg)
    return raw


def _parse_race_date(item: Mapping[str, Any]) -> date:
    v = item.get("race_date")
    if isinstance(v, str) and len(v) >= 10:
        try:
            return date.fromisoformat(v[:10])
        except ValueError:
            pass
    rid = str(item.get("race_id", ""))
    if len(rid) >= 8 and rid[:8].isdigit():
        return date(int(rid[:4]), int(rid[4:6]), int(rid[6:8]))
    return date(2000, 1, 1)


def _horse_id_map(race_id: str, raw_rows: list[Any]) -> dict[int, str]:
    m: dict[int, str] = {}
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        num = int(row.get("horse_number") or row.get("number") or 0)
        if num < 1:
            continue
        hid = row.get("horse_id")
        m[num] = str(hid) if hid else f"{race_id}_h{num}"
    return m


def _entry_rows_for_race(data: Mapping[str, Any], rid: str) -> list[Any]:
    bucket = data.get("entries_by_race") or data.get("entries") or {}
    if isinstance(bucket, dict):
        eraw = bucket.get(rid) or bucket.get(str(rid))
        if isinstance(eraw, list) and eraw:
            return eraw
    races = data.get("races") or []
    if isinstance(races, list):
        for item in races:
            if not isinstance(item, dict):
                continue
            if str(item.get("race_id", "")) != rid:
                continue
            e = item.get("entries") or []
            return e if isinstance(e, list) else []
    return []


def _entry_defaults(race_id: str, row: Mapping[str, Any]) -> dict[str, Any]:
    hid = row.get("horse_id") or f"{race_id}_h{row.get('horse_number', 0)}"
    num = int(row.get("horse_number") or row.get("number") or 1)
    return {
        "race_id": race_id,
        "horse_id": str(hid),
        "horse_name": str(row.get("horse_name") or row.get("name") or "unknown"),
        "post_position": int(row.get("post_position") or row.get("frame") or num),
        "horse_number": num,
        "jockey_id": str(row.get("jockey_id") or "-"),
        "jockey_name": str(row.get("jockey_name") or "-"),
        "trainer_id": str(row.get("trainer_id") or "-"),
        "weight_carried": float(row.get("weight_carried") or 55.0),
        "horse_weight": row.get("horse_weight"),
        "horse_weight_change": row.get("horse_weight_change"),
        "odds_win": float(row["odds_win"]) if row.get("odds_win") is not None else None,
        "popularity": int(row["popularity"]) if row.get("popularity") is not None else None,
    }


def _result_defaults(
    race_id: str,
    row: Mapping[str, Any],
    id_by_num: Mapping[int, str],
) -> dict[str, Any]:
    num = int(row.get("horse_number") or row.get("number") or 0)
    hid = row.get("horse_id") or id_by_num.get(num) or ""
    return {
        "race_id": race_id,
        "horse_id": str(hid),
        "horse_number": num,
        "finish_position": int(row.get("finish_position") or row.get("position") or 99),
        "finish_time": row.get("finish_time"),
        "margin": row.get("margin"),
        "last_3f": row.get("last_3f"),
        "corner_positions": row.get("corner_positions"),
    }


def load_races(path: Path | str) -> list[RaceRecord]:
    """JSON の races 配列を RaceRecord にする。不正行はスキップ。"""
    data = _read_json(path)
    rows = data.get("races") or []
    out: list[RaceRecord] = []
    if not isinstance(rows, list):
        return out
    for item in rows:
        if not isinstance(item, dict):
            continue
        try:
            rec = RaceRecord(
                race_id=str(item["race_id"]),
                race_date=_parse_race_date(item),
                race_number=int(item["race_number"]),
                distance=int(item["distance"]),
                track_condition=item["track_condition"],
                grade=item["grade"],
                num_runners=int(item["num_runners"]),
                post_time=item.get("post_time"),
            )
        except (KeyError, TypeError, ValueError):
            continue
        out.append(rec)
    return out


def load_entries(path: Path | str) -> dict[str, list[HorseEntry]]:
    """race_id -> HorseEntry[]。

    2形式を許容:
      A) entries_by_race: {race_id: [...]} — フラット形式
      B) races[].entries: [...] — ネスト形式（sample_races.json）
    """
    data = _read_json(path)

    # 形式A: トップレベルに entries_by_race / entries がある場合
    bucket = data.get("entries_by_race") or data.get("entries") or {}
    if isinstance(bucket, dict) and bucket:
        out: dict[str, list[HorseEntry]] = {}
        for rid, rows in bucket.items():
            if not isinstance(rows, list):
                continue
            acc: list[HorseEntry] = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                try:
                    acc.append(HorseEntry.model_validate(_entry_defaults(str(rid), row)))
                except (TypeError, ValueError):
                    continue
            out[str(rid)] = acc
        return out

    # 形式B: races[].entries にネストされている場合
    races = data.get("races") or []
    if not isinstance(races, list):
        return {}
    out2: dict[str, list[HorseEntry]] = {}
    for item in races:
        if not isinstance(item, dict):
            continue
        rid = str(item.get("race_id", ""))
        rows = item.get("entries") or []
        if not isinstance(rows, list):
            continue
        acc2: list[HorseEntry] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                acc2.append(HorseEntry.model_validate(_entry_defaults(rid, row)))
            except (TypeError, ValueError):
                continue
        if acc2:
            out2[rid] = acc2
    return out2


def load_results(path: Path | str) -> dict[str, list[RaceResult]]:
    """race_id -> RaceResult[]。

    2形式を許容:
      A) results_by_race: {race_id: [...]} — フラット形式
      B) races[].results: [...] — ネスト形式（sample_races.json）
    """
    data = _read_json(path)

    # 形式A
    bucket = data.get("results_by_race") or data.get("results") or {}
    if isinstance(bucket, dict) and bucket:
        out: dict[str, list[RaceResult]] = {}
        for rid, rows in bucket.items():
            if not isinstance(rows, list):
                continue
            rid_s = str(rid)
            id_by_num = _horse_id_map(rid_s, _entry_rows_for_race(data, rid_s))
            acc: list[RaceResult] = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                try:
                    payload = _result_defaults(rid_s, row, id_by_num)
                    if int(payload["horse_number"]) < 1:
                        continue
                    if not str(payload.get("horse_id") or ""):
                        continue
                    acc.append(RaceResult.model_validate(payload))
                except (TypeError, ValueError):
                    continue
            out[rid_s] = acc
        return out

    # 形式B: ネスト形式
    races = data.get("races") or []
    if not isinstance(races, list):
        return {}
    out2: dict[str, list[RaceResult]] = {}
    for item in races:
        if not isinstance(item, dict):
            continue
        rid = str(item.get("race_id", ""))
        rows = item.get("results") or []
        if not isinstance(rows, list):
            continue
        ent_rows = item.get("entries") or []
        id_by_num = _horse_id_map(rid, ent_rows) if isinstance(ent_rows, list) else {}
        acc2: list[RaceResult] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                payload = _result_defaults(rid, row, id_by_num)
                if int(payload["horse_number"]) < 1:
                    continue
                if not str(payload.get("horse_id") or ""):
                    continue
                acc2.append(RaceResult.model_validate(payload))
            except (TypeError, ValueError):
                continue
        if acc2:
            out2[rid] = acc2
    return out2


def validate_race_bundle(
    races: list[RaceRecord],
    entries: dict[str, list[HorseEntry]],
    results: dict[str, list[RaceResult]],
) -> list[str]:
    """整合チェック（警告のみ・例外にしない）。"""
    warns: list[str] = []
    ids = {r.race_id for r in races}
    for rid in ids:
        if rid not in entries:
            warns.append(f"no entries for race_id={rid}")
            continue
        er = entries[rid]
        r = next((x for x in races if x.race_id == rid), None)
        if r is not None and len(er) != r.num_runners:
            warns.append(
                f"race_id={rid} num_runners={r.num_runners} but entries={len(er)}",
            )
        nums = {e.horse_number for e in er}
        rs = results.get(rid, [])
        nums_res = {x.horse_number for x in rs}
        for res in rs:
            if res.horse_number not in nums:
                warns.append(
                    f"race_id={rid} result horse_number={res.horse_number} not in entries",
                )
        missing_fin = nums - nums_res
        if missing_fin:
            warns.append(
                f"race_id={rid} entries without result for horse_numbers={sorted(missing_fin)}",
            )
        if r is not None and rs and len(rs) != r.num_runners:
            warns.append(
                f"race_id={rid} num_runners={r.num_runners} but results={len(rs)}",
            )
    for rid in entries:
        if rid not in ids:
            warns.append(f"entries present for unknown race_id={rid}")
    for rid in results:
        if rid not in ids:
            warns.append(f"results present for unknown race_id={rid}")
    return warns
