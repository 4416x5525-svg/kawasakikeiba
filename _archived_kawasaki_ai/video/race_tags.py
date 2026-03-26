"""レース映像タグ定義と主／補助の件数制約。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

MAX_MAIN_TAGS = 2
MAX_AUXILIARY_TAGS = 2


class MainRaceTag(StrEnum):
    """主タグ（展開の骨格: 位置・ペース・勝敗因）。最大2件まで。"""

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
    """補助タグ（走行・直線の細目）。最大2件まで。主タグと値は重複しない。"""

    WIDE_RUNNING = "wide_running"
    RAIL_RUNNING = "rail_running"
    BLOCKED = "blocked"
    STUMBLE = "stumble"
    SWITCHED_LATE = "switched_late"
    STRONG_FINISH = "strong_finish"
    FADING = "fading"


class TagConstraintError(ValueError):
    """主タグ／補助タグの件数・重複が制約に合わないとき。"""


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
    """1頭あたりの確定タグ集合（記録用）。主最大2・補助最大2・重複なし。"""

    main: tuple[MainRaceTag, ...]
    auxiliary: tuple[AuxiliaryRaceTag, ...] = ()

    def __post_init__(self) -> None:
        validate_race_tag_selection(self.main, self.auxiliary)


def validate_race_tag_selection(
    main: tuple[MainRaceTag, ...],
    auxiliary: tuple[AuxiliaryRaceTag, ...] = (),
) -> None:
    """主タグ最大2、補助タグ最大2、同一タグの重複なし。"""
    m_vals = tuple(t.value for t in main)
    a_vals = tuple(t.value for t in auxiliary)
    if len(_dedupe_preserve_order(m_vals)) != len(main):
        msg = "main tags must not contain duplicates"
        raise TagConstraintError(msg)
    if len(_dedupe_preserve_order(a_vals)) != len(auxiliary):
        msg = "auxiliary tags must not contain duplicates"
        raise TagConstraintError(msg)
    if len(main) > MAX_MAIN_TAGS:
        msg = f"main tags: at most {MAX_MAIN_TAGS}, got {len(main)}"
        raise TagConstraintError(msg)
    if len(auxiliary) > MAX_AUXILIARY_TAGS:
        msg = f"auxiliary tags: at most {MAX_AUXILIARY_TAGS}, got {len(auxiliary)}"
        raise TagConstraintError(msg)


def race_tag_selection(
    main: tuple[MainRaceTag, ...],
    auxiliary: tuple[AuxiliaryRaceTag, ...] = (),
) -> RaceTagSelection:
    """検証付きで RaceTagSelection を構築する。"""
    return RaceTagSelection(main=main, auxiliary=auxiliary)
