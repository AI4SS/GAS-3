from __future__ import annotations

from app.schema.news_state import NewsState
from app.schema.simulation import EnvironmentState, RoundSummary


def build_environment_state(news_state: NewsState, round_summary: RoundSummary, total_rounds: int) -> EnvironmentState:
    round_id = round_summary.round_id
    reference_traffic = news_state.benchmark_traffic.get(f"day{round_id}", 0)
    actual_traffic = round_summary.total_metrics["views"]
    trend_alignment_score = 0.0
    if reference_traffic > 0:
        trend_alignment_score = max(0.0, 1.0 - abs(actual_traffic - reference_traffic) / reference_traffic)

    comment_count = len(news_state.comment_threads)
    if comment_count == 0:
        comment_climate = "sparse"
    elif comment_count <= 3:
        comment_climate = "forming"
    else:
        comment_climate = "dense"

    intervention_pressure = min(1.0, 0.25 * len(news_state.interventions) + round_summary.total_metrics["comments"] / 200000)

    if actual_traffic >= 10_000_000:
        heat_stage = "explosive"
    elif actual_traffic >= 2_000_000:
        heat_stage = "hot"
    else:
        heat_stage = "emerging"

    peak_day = 1
    if news_state.benchmark_traffic:
        peak_key, _ = max(news_state.benchmark_traffic.items(), key=lambda item: item[1])
        peak_day = int(str(peak_key).replace("day", ""))

    if total_rounds <= 1 or round_id == 1:
        lifecycle = "initial outbreak"
    elif round_id < peak_day:
        lifecycle = "rapid diffusion"
    elif round_id == peak_day:
        lifecycle = "peak attention"
    elif round_id < total_rounds:
        lifecycle = "stabilization"
    else:
        lifecycle = "long-tail decay"

    return EnvironmentState(
        heat_stage=heat_stage,
        event_lifecycle_stage=lifecycle,
        dominant_sentiment=round_summary.dominant_sentiment,
        intervention_pressure=round(intervention_pressure, 4),
        comment_climate=comment_climate,
        trend_alignment_score=round(trend_alignment_score, 4),
        reference_traffic=reference_traffic,
    )
