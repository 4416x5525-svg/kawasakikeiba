"""サブシステム生スコアを共通バンド [-2, +2] へ正規化する。"""

from __future__ import annotations

import math


def rescale_to_band(
    raw: float,
    *,
    src_low: float,
    src_high: float,
    dst_low: float = -2.0,
    dst_high: float = 2.0,
) -> float:
    """[src_low, src_high] に線形写像し、域外はクリップして [dst_low, dst_high] を返す。"""
    if math.isnan(raw) or math.isinf(raw):
        msg = "raw must be finite (not NaN/inf)"
        raise ValueError(msg)
    if src_high <= src_low:
        msg = "src_high must be greater than src_low"
        raise ValueError(msg)
    if dst_high <= dst_low:
        msg = "dst_high must be greater than dst_low"
        raise ValueError(msg)
    clamped = min(max(raw, src_low), src_high)
    t = (clamped - src_low) / (src_high - src_low)
    return dst_low + t * (dst_high - dst_low)


def normalize_core_score(
    raw: float,
    *,
    src_low: float = -1.0,
    src_high: float = 1.0,
) -> float:
    """Core 由来スコア（既定: [-1,1] 想定）を [-2, 2] へ。"""
    return rescale_to_band(raw, src_low=src_low, src_high=src_high)


def normalize_race_score(
    raw: float,
    *,
    src_low: float = -1.0,
    src_high: float = 1.0,
) -> float:
    """レース映像集約スコア（既定: [-1,1] 想定）を [-2, 2] へ。"""
    return rescale_to_band(raw, src_low=src_low, src_high=src_high)


def normalize_paddock_score(
    raw: float,
    *,
    src_low: float = -1.0,
    src_high: float = 1.0,
) -> float:
    """パドックスコア（既定: [-1,1] 想定）を [-2, 2] へ。"""
    return rescale_to_band(raw, src_low=src_low, src_high=src_high)


def normalize_warmup_score(
    raw: float,
    *,
    src_low: float = -1.0,
    src_high: float = 1.0,
) -> float:
    """返し馬スコア（既定: [-1,1] 想定）を [-2, 2] へ。"""
    return rescale_to_band(raw, src_low=src_low, src_high=src_high)
