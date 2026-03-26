"""Popularity baseline.

人気順位のみに基づくスコア生成。
全モデルはこのベースラインを上回る必要がある。

比較用に、単勝オッズ順（低オッズ＝仮1位）へ同じ調和級数を当てる
``generate_odds_rank_baseline_predictions``、および市場確率を均等へ滑らかに寄せる
``generate_shrinkage_baseline_predictions``（P = α×市場 + (1-α)/N）も用意する。
"""

from __future__ import annotations

from kawasaki_keiba.schemas.prediction import CorePrediction
from kawasaki_keiba.schemas.race import HorseEntry


def popularity_win_prob(popularity: int, num_runners: int) -> float:
    """人気順位から勝率を推定する（調和級数ベース）。

    P(win | rank=k, N) = (1/k) / Σ(1/i, i=1..N)
    """
    if popularity < 1:
        msg = f"popularity must be >= 1, got {popularity}"
        raise ValueError(msg)
    if num_runners < 1:
        msg = f"num_runners must be >= 1, got {num_runners}"
        raise ValueError(msg)
    if popularity > num_runners:
        msg = f"popularity ({popularity}) > num_runners ({num_runners})"
        raise ValueError(msg)
    harmonic_sum = sum(1.0 / i for i in range(1, num_runners + 1))
    return (1.0 / popularity) / harmonic_sum


def popularity_place_prob(
    popularity: int,
    num_runners: int,
    *,
    places: int = 3,
) -> float:
    """人気順位から複勝圏確率を推定する。

    簡易推定: place_prob = min(1.0, win_prob * num_runners / places)
    5頭以下は places=2 相当に調整。
    """
    effective_places = min(places, 2) if num_runners <= 4 else places
    win_p = popularity_win_prob(popularity, num_runners)
    return min(1.0, win_p * num_runners / effective_places)


def generate_baseline_predictions(
    entries: list[HorseEntry],
    market_probs: dict[int, float] | None = None,
) -> list[CorePrediction]:
    """人気順ベースラインから CorePrediction リストを生成する。

    Args:
        entries: 出走馬リスト（``load_entries`` で得た 1 レース分をそのまま渡せる。
            popularity があるとその順でランク付けする。
        market_probs: {horse_number: market_win_prob} マッピング（あれば）

    Returns:
        CorePrediction リスト。popularity 未設定の馬は馬番順で仮割当。

    Note:
        baseline の edge は「人気順予測 vs 市場」なので、
        市場効率が完全なら edge ≈ 0 になるはず。
    """
    num_runners = len(entries)
    if num_runners == 0:
        return []

    # popularity 未設定の馬に仮順位を割り当てる（馬番順）
    ranked = sorted(entries, key=_popularity_sort_key)
    assigned: list[tuple[HorseEntry, int]] = []
    for rank, entry in enumerate(ranked, start=1):
        assigned.append((entry, rank))

    predictions: list[CorePrediction] = []
    for entry, rank in assigned:
        win_p = popularity_win_prob(rank, num_runners)
        place_p = popularity_place_prob(rank, num_runners)
        rank_score = 1.0 - (rank - 1) / max(num_runners - 1, 1)

        if market_probs and entry.horse_number in market_probs:
            mkt_p = market_probs[entry.horse_number]
        else:
            mkt_p = win_p  # 市場確率不明なら baseline 自身を代入（edge=0）

        predictions.append(
            CorePrediction(
                race_id=entry.race_id,
                horse_id=entry.horse_id,
                horse_number=entry.horse_number,
                rank_score=rank_score,
                win_prob=win_p,
                place_prob=place_p,
                market_win_prob=mkt_p,
                edge_win=win_p - mkt_p,
                edge_place=place_p - mkt_p,  # 簡易: place edge も win market 基準
            ),
        )
    return predictions


def _odds_rank_sort_key(entry: HorseEntry) -> tuple[int, float, int]:
    """オッズ昇順。欠損・非正は後方にまとめ、馬番で安定ソート。"""
    if entry.odds_win is not None and entry.odds_win > 0:
        return (0, float(entry.odds_win), entry.horse_number)
    return (1, 0.0, entry.horse_number)


def generate_odds_rank_baseline_predictions(
    entries: list[HorseEntry],
    market_probs: dict[int, float] | None = None,
) -> list[CorePrediction]:
    """単勝オッズ順ベースライン（調和級数は人気版と同一式）。

    低オッズほど仮ランク 1 に近づけるため、人気とオッズの順位がずれたレースでは
    市場確率との ``edge_win`` 分布が人気順ベースラインと異なる。
    逆FLB（人気1位への過大配分 vs 市場）の緩和傾向を、
    ``compare_baseline_variants`` で数値比較しやすい。
    """
    num_runners = len(entries)
    if num_runners == 0:
        return []

    ranked = sorted(entries, key=_odds_rank_sort_key)
    assigned: list[tuple[HorseEntry, int]] = []
    for rank, entry in enumerate(ranked, start=1):
        assigned.append((entry, rank))

    predictions: list[CorePrediction] = []
    for entry, rank in assigned:
        win_p = popularity_win_prob(rank, num_runners)
        place_p = popularity_place_prob(rank, num_runners)
        rank_score = 1.0 - (rank - 1) / max(num_runners - 1, 1)

        if market_probs and entry.horse_number in market_probs:
            mkt_p = market_probs[entry.horse_number]
        else:
            mkt_p = win_p

        predictions.append(
            CorePrediction(
                race_id=entry.race_id,
                horse_id=entry.horse_id,
                horse_number=entry.horse_number,
                rank_score=rank_score,
                win_prob=win_p,
                place_prob=place_p,
                market_win_prob=mkt_p,
                edge_win=win_p - mkt_p,
                edge_place=place_p - mkt_p,
            ),
        )
    return predictions


def generate_shrinkage_baseline_predictions(
    entries: list[HorseEntry],
    market_probs: dict[int, float],
    *,
    alpha: float = 0.8,
) -> list[CorePrediction]:
    """Shrinkage baseline: 市場確率を均等確率方向にシフトする。

    P_shrink(i) = α × market_prob(i) + (1 - α) × (1 / N)

    Args:
        entries: 出走馬リスト
        market_probs: {horse_number: market_win_prob}
        alpha: 市場信頼度 [0, 1]。1.0=市場そのまま、0.0=均等確率。

    仮説:
        市場は人気馬を過大評価し、穴馬を過小評価する傾向がある（FLB）。
        α < 1 にすることで「市場の過信」を補正する。
        edge < 0 の人気馬 = 市場が過大評価していると仮定。
        edge > 0 の穴馬 = 市場が過小評価していると仮定。
    """
    num_runners = len(entries)
    if num_runners == 0:
        return []
    if not (0.0 <= alpha <= 1.0):
        msg = f"alpha must be in [0, 1], got {alpha}"
        raise ValueError(msg)

    uniform = 1.0 / num_runners

    predictions: list[CorePrediction] = []
    for entry in entries:
        mkt_p = market_probs.get(entry.horse_number, uniform)
        shrink_p = alpha * mkt_p + (1.0 - alpha) * uniform
        place_p = min(1.0, shrink_p * num_runners / 3)

        # rank_score: shrink_p 降順
        predictions.append(
            CorePrediction(
                race_id=entry.race_id,
                horse_id=entry.horse_id,
                horse_number=entry.horse_number,
                rank_score=0.0,  # 後で設定
                win_prob=shrink_p,
                place_prob=place_p,
                market_win_prob=mkt_p,
                edge_win=shrink_p - mkt_p,
                edge_place=place_p - mkt_p,
            ),
        )

    # rank_score を shrink_p 降順で割り当て
    sorted_idx = sorted(
        range(len(predictions)),
        key=lambda i: predictions[i].win_prob,
        reverse=True,
    )
    for rank, idx in enumerate(sorted_idx):
        p = predictions[idx]
        predictions[idx] = CorePrediction(
            race_id=p.race_id,
            horse_id=p.horse_id,
            horse_number=p.horse_number,
            rank_score=1.0 - rank / max(len(predictions) - 1, 1),
            win_prob=p.win_prob,
            place_prob=p.place_prob,
            market_win_prob=p.market_win_prob,
            edge_win=p.edge_win,
            edge_place=p.edge_place,
        )

    return predictions


def compare_baseline_variants(
    entries: list[HorseEntry],
    market_probs: dict[int, float],
    *,
    shrinkage_alpha: float = 0.8,
) -> dict[str, object]:
    """1レース分: popularity / odds-rank / shrinkage の3案を並べて返す。

    ``load_entries`` × ``market_probs_from_odds`` と組み合わせて、
    複数レースをループすれば実データ10Rなどの比較がしやすい。
    """
    if not entries:
        return {
            "race_id": "",
            "n_runners": 0,
            "shrinkage_alpha": shrinkage_alpha,
            "popularity_max_abs_edge": 0.0,
            "odds_rank_max_abs_edge": 0.0,
            "shrinkage_max_abs_edge": 0.0,
            "popularity_mean_abs_edge": 0.0,
            "odds_rank_mean_abs_edge": 0.0,
            "shrinkage_mean_abs_edge": 0.0,
        }

    pop_preds = generate_baseline_predictions(entries, market_probs)
    odds_preds = generate_odds_rank_baseline_predictions(entries, market_probs)
    shrink_preds = generate_shrinkage_baseline_predictions(
        entries, market_probs, alpha=shrinkage_alpha,
    )

    def _max_abs(preds: list[CorePrediction]) -> float:
        return max(abs(p.edge_win) for p in preds) if preds else 0.0

    def _mean_abs(preds: list[CorePrediction]) -> float:
        if not preds:
            return 0.0
        return sum(abs(p.edge_win) for p in preds) / len(preds)

    return {
        "race_id": entries[0].race_id,
        "n_runners": len(entries),
        "shrinkage_alpha": shrinkage_alpha,
        "popularity_max_abs_edge": round(_max_abs(pop_preds), 5),
        "odds_rank_max_abs_edge": round(_max_abs(odds_preds), 5),
        "shrinkage_max_abs_edge": round(_max_abs(shrink_preds), 5),
        "popularity_mean_abs_edge": round(_mean_abs(pop_preds), 5),
        "odds_rank_mean_abs_edge": round(_mean_abs(odds_preds), 5),
        "shrinkage_mean_abs_edge": round(_mean_abs(shrink_preds), 5),
    }


def describe_baseline_predictions(preds: list[CorePrediction]) -> dict[str, object]:
    """``generate_baseline_predictions`` の戻り値を要約（ログ・assert 用）。"""
    if not preds:
        return {"n_predictions": 0}
    edges = [p.edge_win for p in preds]
    return {
        "n_predictions": len(preds),
        "race_id": preds[0].race_id,
        "edge_win_mean": sum(edges) / len(edges),
        "edge_win_min": min(edges),
        "edge_win_max": max(edges),
    }


def _popularity_sort_key(entry: HorseEntry) -> tuple[int, int]:
    """popularity があれば優先、なければ馬番順で後ろに回す。"""
    if entry.popularity is not None:
        return (0, entry.popularity)
    return (1, entry.horse_number)
