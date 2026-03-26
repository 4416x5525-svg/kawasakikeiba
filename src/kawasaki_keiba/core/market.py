"""オッズ → 市場確率変換。

単勝オッズから implied probability を算出し、
オーバーラウンドを除去して正規化する。
"""

from __future__ import annotations


def odds_to_implied_prob(odds: float) -> float:
    """単勝オッズから implied probability を算出する。

    P_implied = 1 / odds
    """
    if odds <= 0:
        msg = f"odds must be positive, got {odds}"
        raise ValueError(msg)
    return 1.0 / odds


def normalize_probs(probs: list[float]) -> list[float]:
    """オーバーラウンドを除去して確率の合計を 1.0 にする。

    各 implied prob を合計で割る（比例正規化）。
    """
    total = sum(probs)
    if total <= 0:
        msg = "sum of probabilities must be positive"
        raise ValueError(msg)
    return [p / total for p in probs]


def market_probs_from_odds(odds_list: list[float]) -> list[float]:
    """オッズリストから正規化済み市場確率を返す。

    Args:
        odds_list: 各馬の単勝オッズ（確定値）

    Returns:
        正規化済み市場推定勝率（合計 ≈ 1.0）

    Example:
        >>> market_probs_from_odds([2.0, 4.0, 8.0])
        [0.571..., 0.285..., 0.142...]
    """
    if not odds_list:
        msg = "odds_list must not be empty"
        raise ValueError(msg)
    implied = [odds_to_implied_prob(o) for o in odds_list]
    return normalize_probs(implied)


def overround(odds_list: list[float]) -> float:
    """オーバーラウンド率を算出する。

    100% を超えた分が胴元の取り分。
    川崎競馬は 120-130% 程度が典型。

    Returns:
        オーバーラウンド率（例: 1.25 = 125%）
    """
    if not odds_list:
        msg = "odds_list must not be empty"
        raise ValueError(msg)
    return sum(odds_to_implied_prob(o) for o in odds_list)
