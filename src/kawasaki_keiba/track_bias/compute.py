"""Track Bias の算出ロジック。

当日の確定レース結果から枠番バイアス・脚質バイアスを計算する。
"""

from __future__ import annotations

from datetime import date

from kawasaki_keiba.schemas.race import HorseEntry, RaceRecord, RaceResult, TrackCondition
from kawasaki_keiba.track_bias.snapshot import TrackBiasSnapshot

# 最小レース数: これ未満では confidence=0
MIN_RACES_FOR_BIAS = 3
# 少頭数レースはバイアス算出から除外
MIN_RUNNERS_FOR_BIAS = 6


def _parse_corners(s: str | None) -> list[int] | None:
    """'1-2-3-4' 形式を [1,2,3,4] にパース。"""
    if not s:
        return None
    parts = s.split("-")
    try:
        return [int(x.strip()) for x in parts if x.strip()]
    except ValueError:
        return None


def _confidence_from_sample(n: int, *, min_n: int = MIN_RACES_FOR_BIAS, max_n: int = 12) -> float:
    """サンプル数から [0, 1] の信頼度を算出。"""
    if n < min_n:
        return 0.0
    return min(1.0, (n - min_n + 1) / (max_n - min_n + 1))


def compute_post_bias(
    entries: list[HorseEntry],
    results: list[RaceResult],
) -> float:
    """枠番バイアスを算出する。

    内枠（下半分）の馬の人気補正後着順率 vs 外枠（上半分）の馬の着順率。
    負 = 内有利、正 = 外有利。
    """
    if not entries or not results:
        return 0.0

    num_runners = len(entries)
    if num_runners < MIN_RUNNERS_FOR_BIAS:
        return 0.0

    mid = num_runners / 2
    result_map = {r.horse_number: r.finish_position for r in results}
    pop_map = {e.horse_number: e.popularity for e in entries}

    inner_rates: list[float] = []
    outer_rates: list[float] = []

    for entry in entries:
        fp = result_map.get(entry.horse_number)
        if fp is None:
            continue
        rate = 1.0 - (fp - 1) / max(num_runners - 1, 1)
        pop = pop_map.get(entry.horse_number)
        # 人気補正: 人気が良いほど着順率が高いのは当然なので、
        # 人気順位を差し引いて「枠純粋の寄与」を推定する
        expected_rate = 1.0 - ((pop or num_runners // 2) - 1) / max(num_runners - 1, 1)
        adjusted = rate - expected_rate

        if entry.post_position <= mid:
            inner_rates.append(adjusted)
        else:
            outer_rates.append(adjusted)

    if not inner_rates or not outer_rates:
        return 0.0

    inner_avg = sum(inner_rates) / len(inner_rates)
    outer_avg = sum(outer_rates) / len(outer_rates)

    # 負 = 内有利（内枠の補正後着順率が高い）
    raw = outer_avg - inner_avg
    return max(-1.0, min(1.0, raw * 5.0))  # スケーリング


def compute_pace_bias(
    results: list[RaceResult],
    num_runners: int,
) -> float:
    """脚質バイアスを算出する。

    先行勢（1-2角通過上位1/3）vs 差し勢（下位1/3）の着順率差。
    負 = 先行有利、正 = 差し有利。
    """
    if not results or num_runners < MIN_RUNNERS_FOR_BIAS:
        return 0.0

    with_corners: list[tuple[int, int]] = []  # (early_position, finish_position)
    for r in results:
        corners = _parse_corners(r.corner_positions)
        if corners and len(corners) >= 2:
            early = corners[0]  # 1角通過順
            with_corners.append((early, r.finish_position))

    if len(with_corners) < 4:
        return 0.0

    with_corners.sort(key=lambda x: x[0])
    third = max(1, len(with_corners) // 3)

    leaders = with_corners[:third]
    closers = with_corners[-third:]

    leader_rate = sum(1.0 - (fp - 1) / max(num_runners - 1, 1) for _, fp in leaders) / len(leaders)
    closer_rate = sum(1.0 - (fp - 1) / max(num_runners - 1, 1) for _, fp in closers) / len(closers)

    # 負 = 先行有利
    raw = closer_rate - leader_rate
    return max(-1.0, min(1.0, raw * 5.0))


def compute_track_bias(
    races: list[RaceRecord],
    all_entries: dict[str, list[HorseEntry]],
    all_results: dict[str, list[RaceResult]],
    *,
    target_date: date | None = None,
    target_distance: int | None = None,
) -> TrackBiasSnapshot:
    """当日のレース結果からTrackBiasSnapshotを算出する。

    Args:
        races: 当日のRaceRecordリスト（R番号順）。
            ``load_races`` の戻り値をそのまま渡せる。
        all_entries: {race_id: [HorseEntry]} マッピング（``load_entries``）
        all_results: {race_id: [RaceResult]} マッピング（``load_results``）
        target_date: 対象日（Noneなら最初のレースの日付）
        target_distance: 特定距離に絞る（Noneなら全距離）
    """
    if not races:
        d = target_date or date.today()
        return TrackBiasSnapshot(
            race_date=d, distance=target_distance or 0,
            track_condition=TrackCondition.GOOD,
            computed_after_race=0,
            post_bias=0.0, pace_bias=0.0,
            post_confidence=0.0, pace_confidence=0.0,
            sample_races=0,
            short_reason="レース結果なし",
        )

    filtered = races
    if target_distance:
        filtered = [r for r in races if r.distance == target_distance]

    post_biases: list[float] = []
    pace_biases: list[float] = []

    for race in filtered:
        entries = all_entries.get(race.race_id, [])
        results = all_results.get(race.race_id, [])
        if not entries or not results:
            continue
        if race.num_runners < MIN_RUNNERS_FOR_BIAS:
            continue

        pb = compute_post_bias(entries, results)
        post_biases.append(pb)

        pcb = compute_pace_bias(results, race.num_runners)
        pace_biases.append(pcb)

    sample = len(post_biases)
    avg_post = sum(post_biases) / sample if sample else 0.0
    avg_pace = sum(pace_biases) / sample if sample else 0.0
    post_conf = _confidence_from_sample(sample)
    pace_conf = _confidence_from_sample(sample)

    rd = target_date or races[0].race_date
    tc = races[0].track_condition

    # 短い理由文を生成
    parts: list[str] = []
    if post_conf >= 0.2:
        if avg_post < -0.2:
            parts.append(f"内枠有利({avg_post:+.2f})")
        elif avg_post > 0.2:
            parts.append(f"外枠有利({avg_post:+.2f})")
    if pace_conf >= 0.2:
        if avg_pace < -0.2:
            parts.append(f"先行有利({avg_pace:+.2f})")
        elif avg_pace > 0.2:
            parts.append(f"差し有利({avg_pace:+.2f})")
    reason = "・".join(parts) if parts else f"{sample}R集計: 顕著な傾向なし"

    return TrackBiasSnapshot(
        race_date=rd,
        distance=target_distance or 0,
        track_condition=tc,
        computed_after_race=max((r.race_number for r in filtered), default=0),
        post_bias=round(avg_post, 4),
        pace_bias=round(avg_pace, 4),
        post_confidence=round(post_conf, 4),
        pace_confidence=round(pace_conf, 4),
        sample_races=sample,
        short_reason=reason,
    )


def describe_track_bias_snapshot(snap: TrackBiasSnapshot) -> dict[str, object]:
    """``compute_track_bias`` の返り値をログ・print 向け dict にまとめる。

    ``TrackBiasSnapshot.to_dict()`` のエイリアス。
    """
    return snap.to_dict()
