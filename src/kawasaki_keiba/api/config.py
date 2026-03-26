"""API 設定。プロジェクトルートの解決。"""

from __future__ import annotations

import os
from pathlib import Path


def _find_project_root() -> Path:
    """プロジェクトルートを探す。

    優先順位:
      1. 環境変数 KAWASAKI_PROJECT_ROOT
      2. カレントディレクトリに web/ がある → カレント
      3. __file__ から上方向に web/ を探す（ローカル開発用フォールバック）
    """
    env = os.environ.get("KAWASAKI_PROJECT_ROOT")
    if env:
        return Path(env)

    cwd = Path.cwd()
    if (cwd / "web").is_dir():
        return cwd

    # __file__ から上に辿る（pip install -e . のローカル開発用）
    p = Path(__file__).resolve().parent
    for _ in range(6):
        if (p / "web").is_dir():
            return p
        p = p.parent

    return cwd


PROJECT_ROOT = _find_project_root()

DATA_PATH = PROJECT_ROOT / "data" / "raw" / "sample_races.json"
