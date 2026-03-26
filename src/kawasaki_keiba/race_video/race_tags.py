"""Race Video タグ体系（kawasaki_keiba.race_video）。

記録上の契約:
  - 主タグ (MainRaceTag): 最大 MAX_MAIN_TAGS 件、同一値の重複不可
  - 補助タグ (AuxiliaryRaceTag): 最大 MAX_AUXILIARY_TAGS 件、同一値の重複不可
  - 主と補助は別 enum（値域分離）。映像解析アルゴリズムは別モジュール。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

MAX_MAIN_TAGS: int = 2
MAX_AUXILIARY_TAGS: int = 2


class MainRaceTag(StrEnum):
    """主タグ（位置・ペース・勝敗因の骨格）。"""

    POSITION_FRONT = "position_front"
    POSITION_MIDDLE = "position_middle"
    POSITION_REAR = "position_rear"
    PACE_FAST = "pace_fast"
    PACE_SLOW = "pace_slow"
    LOSS_PACE = "loss_pace"
    LOSS_POSITION = "loss_position"
    LOSS_BLOCKED = "loss_blocked"
    LOSS_CONDITION = "loss_condition"
    WIN_PACE_FIT = "win_pace_fit"
    WIN_POSITION = "win_position"
    WIN_STRONG_KICK = "win_strong_kick"


class AuxiliaryRaceTag(StrEnum):
    """補助タグ（走行・直線の細目）。主タグと値は別集合。"""

    WIDE_RUNNING = "wide_running"
    RAIL_RUNNING = "rail_running"
    BLOCKED = "blocked"
    STUMBLE = "stumble"
    SWITCHED_LATE = "switched_late"
    STRONG_FINISH = "strong_finish"
    FADING = "fading"


class TagConstraintError(ValueError):
    """タグ件数または重複が契約に違反するとき。"""


def _dedupe_preserve_order(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for x in values:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return tuple(out)


@dataclass(frozen=True)
class RaceTagSelection:
    """1頭分の確定タグ（検証済み）。"""

    main: tuple[MainRaceTag, ...]
    auxiliary: tuple[AuxiliaryRaceTag, ...] = ()

    def __post_init__(self) -> None:
        validate_race_tag_selection(self.main, self.auxiliary)


def validate_race_tag_selection(
    main: Sequence[MainRaceTag],
    auxiliary: Sequence[AuxiliaryRaceTag] = (),
) -> None:
    """検証: 主≤MAX_MAIN_TAGS、補助≤MAX_AUXILIARY_TAGS、その後バケット内重複なし。"""
    if len(main) > MAX_MAIN_TAGS:
        msg = f"main tags: at most {MAX_MAIN_TAGS}, got {len(main)}"
        raise TagConstraintError(msg)
    if len(auxiliary) > MAX_AUXILIARY_TAGS:
        msg = f"auxiliary tags: at most {MAX_AUXILIARY_TAGS}, got {len(auxiliary)}"
        raise TagConstraintError(msg)
    m_vals = tuple(t.value for t in main)
    a_vals = tuple(t.value for t in auxiliary)
    if len(_dedupe_preserve_order(m_vals)) != len(main):
        msg = "main tags must not contain duplicates"
        raise TagConstraintError(msg)
    if len(_dedupe_preserve_order(a_vals)) != len(auxiliary):
        msg = "auxiliary tags must not contain duplicates"
        raise TagConstraintError(msg)


def race_tag_selection(
    main: Sequence[MainRaceTag],
    auxiliary: Sequence[AuxiliaryRaceTag] = (),
) -> RaceTagSelection:
    """契約検証後に RaceTagSelection を返す。"""
    return RaceTagSelection(main=tuple(main), auxiliary=tuple(auxiliary))
