"""データディレクトリおよびリポジトリ基準パス。"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from kawasaki_keiba.config import SystemModule

DEFAULT_DATA_DIRNAME = "data"


def package_dir() -> Path:
    """kawasaki_keiba パッケージディレクトリ。"""
    return Path(__file__).resolve().parent


def project_root() -> Path:
    """リポジトリルート（src の親）。"""
    return package_dir().parent.parent


def data_root(*, base: Path | None = None, dirname: str = DEFAULT_DATA_DIRNAME) -> Path:
    """データツリーのルート。base 未指定時は project_root() / dirname。"""
    root = base if base is not None else project_root()
    return (root / dirname).resolve()


def data_layout(root: Path | None = None) -> Mapping[str, Path]:
    """標準サブディレクトリ。"""
    base = data_root() if root is None else root.resolve()
    return {
        "root": base,
        "raw": base / "raw",
        "interim": base / "interim",
        "processed": base / "processed",
        "external": base / "external",
        "artifacts": base / "artifacts",
        "cache": base / "cache",
        "logs": base / "logs",
    }


def suggested_module_paths(
    data_base: Path | None = None,
) -> Mapping[SystemModule, Path]:
    """各 SystemModule 用の推奨ルート（artifacts 下）。"""
    layout = data_layout(data_base)
    art = layout["artifacts"]
    return {
        SystemModule.CORE: art / "core",
        SystemModule.GATE: art / "gate",
        SystemModule.RACE_VIDEO: art / "race_video",
        SystemModule.PADDOCK: art / "paddock",
        SystemModule.WARMUP: art / "warmup",
        SystemModule.INTEGRATION: art / "integration",
        SystemModule.MONITORING: art / "monitoring",
        SystemModule.LOGGING: art / "logging",
    }
