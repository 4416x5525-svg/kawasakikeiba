"""Track Bias: 当日レース結果からリアルタイムに馬場傾向を算出する。

off / advisory / integrated の3モード。初期は advisory 専用。
Gate には接続しない。ダッシュボード表示のみ。
"""

from kawasaki_keiba.track_bias.snapshot import TrackBiasSnapshot
from kawasaki_keiba.track_bias.compute import compute_track_bias

__all__ = ["TrackBiasSnapshot", "compute_track_bias"]
