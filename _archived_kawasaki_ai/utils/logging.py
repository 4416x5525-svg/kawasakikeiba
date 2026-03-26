"""ログ初期化とロガー取得の共通入口。"""

from __future__ import annotations

import sys
from importlib import import_module
from typing import Any, TextIO

# このモジュール名が logging のため、標準ライブラリは importlib で明示的に読み込む
_stdlib_logging = import_module("logging")

_LOG_PREFIX = "kawasaki_ai"
_DEFAULT_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def setup_logging(
    *,
    level: int | str = _stdlib_logging.INFO,
    stream: TextIO | None = None,
    fmt: str = _DEFAULT_FORMAT,
    force: bool = True,
) -> None:
    """ルートロガーにハンドラを1つ付与する簡易設定。複数回呼んでも上書き可能（force）。"""
    resolved: int
    if isinstance(level, str):
        resolved = getattr(_stdlib_logging, level.upper(), _stdlib_logging.INFO)
    else:
        resolved = level
    handler = _stdlib_logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(_stdlib_logging.Formatter(fmt))
    _stdlib_logging.basicConfig(level=resolved, handlers=[handler], force=force)


def get_logger(name: str) -> Any:
    """kawasaki_ai 配下のロガー名で取得（標準 logging.Logger インスタンス）。"""
    qual = name if name.startswith(_LOG_PREFIX) else f"{_LOG_PREFIX}.{name}"
    return _stdlib_logging.getLogger(qual)
