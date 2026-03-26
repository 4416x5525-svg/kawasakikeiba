"""Wind: 風向き・風速の影響推定（discard 前提の最小スタブ）。

初期状態は advisory 専用。統計的に有意でなければ discard する。
Gate には接続しない。
"""

from kawasaki_keiba.wind.estimate import WindEstimate, estimate_wind_impact

__all__ = ["WindEstimate", "estimate_wind_impact"]
