from __future__ import annotations

from app.compat.metagpt import ActionBase
from app.schema.agent_state import GroupProfile, GroupState
from app.schema.news_state import NewsState
from app.schema.simulation import RoundContext
from app.services.dynamics import (
    environment_context_text,
    estimate_metrics,
    infer_online_ratio,
    infer_trend_label,
    quantize_metrics_from_ratio,
)
from app.services.llm import LLMGateway


class QuantizeBehavior(ActionBase):
    async def run(
        self,
        profile: GroupProfile,
        state: GroupState,
        news_state: NewsState,
        round_ctx: RoundContext,
        llm_gateway: LLMGateway | None = None,
    ) -> dict[str, int]:
        metrics = await self._request_metrics(profile, state, news_state, round_ctx, llm_gateway)
        if not metrics:
            metrics = estimate_metrics(profile, state, round_ctx)
        state.last_metrics = metrics
        return metrics

    async def _request_metrics(
        self,
        profile: GroupProfile,
        state: GroupState,
        news_state: NewsState,
        round_ctx: RoundContext,
        llm_gateway: LLMGateway | None,
    ) -> dict[str, int] | None:
        if not llm_gateway:
            return None

        if state.news_trend is None:
            trend, trend_type = infer_trend_label(news_state)
            state.news_trend = trend
            state.news_trend_type = trend_type

        online_ratio = infer_online_ratio(profile, state, round_ctx, news_state.benchmark_traffic)

        prompt = f"""
You are {profile.name}.
Your hierarchy path is: {' > '.join(profile.hierarchy_path) or profile.name}.
Your subgroup focus is: {profile.focus_label}. Related keywords: {profile.focus_keywords}.
Today is Day {round_ctx.current_round} of a {round_ctx.total_rounds}-day news cycle.
The population size of your user group is {profile.population}.
Yesterday engagement metrics:
Views: {state.last_metrics['views']}
Likes: {state.last_metrics['likes']}
Comments: {state.last_metrics['comments']}
Shares: {state.last_metrics['shares']}
Total engagement metrics so far:
Views: {news_state.views}
Likes: {news_state.likes}
Comments: {news_state.comments}
Shares: {news_state.shares}
News trend label: {state.news_trend}
News trend type: {state.news_trend_type}
{environment_context_text(round_ctx.previous_environment)}
News context:
{news_state.prompt_context()}

Prediction rules:
1. Estimate the online ratio today based on the population size, current news trend, and previous-round environment state.
2. Return an online_ratio between 0 and 1.
3. Optionally refine the news trend label and trend type.
4. Optionally provide an engagement_multiplier reflecting whether today's interaction intensity should be below, near, or above baseline.

Return JSON:
{{
  "online_ratio": {online_ratio:.4f},
  "news_trend": "{state.news_trend}",
  "news_trend_type": {state.news_trend_type},
  "engagement_multiplier": 1.0
}}
"""
        response = await llm_gateway.complete_json(prompt)
        if not response:
            return None

        state.news_trend = str(response.get("news_trend", state.news_trend))
        state.news_trend_type = int(float(response.get("news_trend_type", state.news_trend_type or 0)))
        suggested_ratio = float(response.get("online_ratio", online_ratio))
        engagement_multiplier = float(response.get("engagement_multiplier", 1.0))
        effective_ratio = max(0.002, min(0.95, suggested_ratio * max(0.6, min(1.5, engagement_multiplier))))
        metrics = quantize_metrics_from_ratio(profile, state, round_ctx, effective_ratio)

        if metrics["likes"] >= metrics["views"]:
            metrics["likes"] = max(1, metrics["views"] // 10)
        if metrics["comments"] >= metrics["likes"]:
            metrics["comments"] = max(0, metrics["likes"] // 10)
        if metrics["shares"] >= metrics["likes"]:
            metrics["shares"] = max(0, metrics["likes"] // 10)
        return metrics
