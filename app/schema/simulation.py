from __future__ import annotations

from pydantic import BaseModel, Field

from app.schema.agent_state import GroupRoundResult


class RoundContext(BaseModel):
    current_round: int
    total_rounds: int
    previous_environment: "EnvironmentState | None" = None


class EnvironmentState(BaseModel):
    heat_stage: str = "emerging"
    event_lifecycle_stage: str = "initial outbreak"
    dominant_sentiment: str = "mixed"
    intervention_pressure: float = 0.0
    comment_climate: str = "sparse"
    trend_alignment_score: float = 0.0
    reference_traffic: int = 0


class RoundSummary(BaseModel):
    round_id: int
    group_results: list[GroupRoundResult] = Field(default_factory=list)
    total_metrics: dict[str, int] = Field(
        default_factory=lambda: {
            "views": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "follows": 0,
        }
    )
    dominant_sentiment: str = "mixed"
    environment_state: EnvironmentState = Field(default_factory=EnvironmentState)


class SimulationResult(BaseModel):
    rounds: list[RoundSummary] = Field(default_factory=list)
