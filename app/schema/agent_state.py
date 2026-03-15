from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class PopulationCategory(str, Enum):
    SUSCEPTIBLE = "susceptible"
    AVERAGE = "average"
    CALM = "calm"

    @property
    def sensitivity(self) -> float:
        return {
            PopulationCategory.SUSCEPTIBLE: 1.0,
            PopulationCategory.AVERAGE: 0.8,
            PopulationCategory.CALM: 0.65,
        }[self]


class EmotionState(BaseModel):
    happiness: float = 0.0
    sadness: float = 0.0
    anger: float = 0.0


class AttitudeState(BaseModel):
    optimism: float = 0.0
    pessimism: float = 0.0
    neutrality: float = 1.0


class InternalSubgroup(BaseModel):
    population: int = 0
    intensity: float = 0.0


class GroupProfile(BaseModel):
    id: str
    name: str
    description: str
    identity: str
    population: int
    characteristic: str
    layer: str = "L1"
    parent_id: str | None = None
    hierarchy_path: list[str] = Field(default_factory=list)
    focus_label: str = "general response"
    focus_keywords: list[str] = Field(default_factory=list)
    category: PopulationCategory = PopulationCategory.AVERAGE


class GroupState(BaseModel):
    emotion: EmotionState = Field(default_factory=EmotionState)
    attitude: AttitudeState = Field(default_factory=AttitudeState)
    polarity: int = -1
    internal_groups: dict[str, InternalSubgroup] = Field(
        default_factory=lambda: {
            "optimism": InternalSubgroup(),
            "pessimism": InternalSubgroup(),
        }
    )
    news_trend: str | None = None
    news_trend_type: int = 0
    news_comments_updated: bool = False
    action_detected: bool = False
    government_agent_intervene: bool = False
    current_round: int = 0
    total_rounds: int = 7
    last_comment: str = ""
    last_metrics: dict[str, int] = Field(
        default_factory=lambda: {
            "views": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "follows": 0,
        }
    )


class GroupRoundResult(BaseModel):
    group_id: str
    group_name: str = ""
    layer: str = "L1"
    hierarchy_path: list[str] = Field(default_factory=list)
    emotion: EmotionState
    attitude: AttitudeState
    polarity: int
    internal_groups: dict[str, InternalSubgroup] = Field(default_factory=dict)
    metrics: dict[str, int]
    comment: str | None = None
