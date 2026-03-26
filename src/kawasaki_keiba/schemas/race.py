"""レース・出走馬・結果のスキーマ定義"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class TrackCondition(StrEnum):
    GOOD = "good"          # 良
    SLIGHTLY_HEAVY = "slightly_heavy"  # 稍重
    HEAVY = "heavy"        # 重
    BAD = "bad"            # 不良


class RaceGrade(StrEnum):
    """川崎競馬の格付け"""
    C3 = "C3"
    C2 = "C2"
    C1 = "C1"
    B3 = "B3"
    B2 = "B2"
    B1 = "B1"
    A2 = "A2"
    A1 = "A1"
    S = "S"
    OPEN = "open"
    STAKES = "stakes"


class RaceRecord(BaseModel):
    """1レースの基本情報"""
    race_id: str = Field(description="一意識別子: YYYYMMDD_KW_RR")
    race_date: date
    race_number: int = Field(ge=1, le=12)
    distance: int = Field(description="距離(m)")
    track_condition: TrackCondition
    grade: RaceGrade
    num_runners: int = Field(ge=2, le=16)
    post_time: datetime | None = None

    @field_validator("race_id")
    @classmethod
    def validate_race_id(cls, v: str) -> str:
        parts = v.split("_")
        if len(parts) != 3 or parts[1] != "KW":
            raise ValueError("race_id must be YYYYMMDD_KW_RR format")
        return v


class HorseEntry(BaseModel):
    """1頭の出走情報"""
    race_id: str
    horse_id: str
    horse_name: str
    post_position: int = Field(ge=1, le=16, description="枠番")
    horse_number: int = Field(ge=1, le=16, description="馬番")
    jockey_id: str
    jockey_name: str
    trainer_id: str
    weight_carried: float = Field(description="斤量(kg)")
    horse_weight: int | None = Field(default=None, description="馬体重(kg)")
    horse_weight_change: int | None = Field(default=None, description="馬体重増減(kg)")
    odds_win: float | None = Field(default=None, description="単勝オッズ（確定）")
    popularity: int | None = Field(default=None, description="単勝人気順")


class RaceResult(BaseModel):
    """1頭の着順結果"""
    race_id: str
    horse_id: str
    horse_number: int
    finish_position: int = Field(ge=1, description="着順")
    finish_time: float | None = Field(default=None, description="走破タイム(秒)")
    margin: str | None = Field(default=None, description="着差")
    last_3f: float | None = Field(default=None, description="上がり3F(秒)")
    corner_positions: str | None = Field(default=None, description="コーナー通過順")


class PastPerformance(BaseModel):
    """過去走データ（1走分）"""
    horse_id: str
    race_id: str
    race_date: date
    distance: int
    track_condition: TrackCondition
    finish_position: int
    num_runners: int
    odds_win: float | None = None
    finish_time: float | None = None
    last_3f: float | None = None
    corner_positions: str | None = None
    horse_weight: int | None = None
    weight_carried: float
    jockey_id: str
    grade: RaceGrade
