from __future__ import annotations

from pydantic import ConfigDict

from app.compat.metagpt import ActionBase
from app.schema.agent_state import GroupProfile, GroupState
from app.schema.news_state import NewsState
from app.schema.simulation import RoundContext
from app.services.dynamics import (
    adjust_internal_groups_from_feedback,
    build_attitude_state,
    build_emotion_state,
    clamp_state,
    detect_polarity,
    environment_context_text,
    keyword_score,
    sync_internal_groups,
)
from app.services.llm import LLMGateway


class AnalyzeGroupResponse(ActionBase):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    llm_gateway: LLMGateway | None = None

    async def run(self, profile: GroupProfile, state: GroupState, news_state: NewsState, round_ctx: RoundContext) -> GroupState:
        llm_state = await self._request_group_state(profile, state, news_state, round_ctx)

        if llm_state:
            state.polarity = self._parse_polarity(llm_state.get("polarity"), state.polarity)
            state.attitude.optimism = float(llm_state.get("optimism", state.attitude.optimism))
            state.attitude.pessimism = float(llm_state.get("pessimism", state.attitude.pessimism))
            state.attitude.neutrality = float(llm_state.get("neutrality", state.attitude.neutrality))
            state.emotion.happiness = float(llm_state.get("happiness", state.emotion.happiness))
            state.emotion.sadness = float(llm_state.get("sadness", state.emotion.sadness))
            state.emotion.anger = float(llm_state.get("anger", state.emotion.anger))
        else:
            score_positive, score_negative = keyword_score(news_state.content)
            state.attitude = build_attitude_state(score_positive, score_negative, profile, round_ctx.previous_environment)
            state.emotion = build_emotion_state(score_positive, score_negative, profile, round_ctx)
            if state.polarity == -1:
                state.polarity = detect_polarity(score_positive, score_negative)

        clamp_state(state)
        state.polarity = detect_polarity(state.attitude.optimism, state.attitude.pessimism)
        state.current_round = round_ctx.current_round
        state.total_rounds = round_ctx.total_rounds
        sync_internal_groups(state, profile.population)
        if news_state.comment_threads or news_state.interventions:
            adjust_internal_groups_from_feedback(state, news_state, profile.population, round_ctx.previous_environment)
        return state

    async def _request_group_state(
        self, profile: GroupProfile, state: GroupState, news_state: NewsState, round_ctx: RoundContext
    ) -> dict | None:
        if not self.llm_gateway:
            return None
        prompt = f"""
You are {profile.name}, {profile.description}.
You are in a simulated environment: Academic Social Network.
You represent {profile.identity} with population {profile.population}.
Your hierarchy path is: {' > '.join(profile.hierarchy_path) or profile.name}.
Your subgroup focus is: {profile.focus_label}. Related keywords: {profile.focus_keywords}.
This is Day {round_ctx.current_round} of a {round_ctx.total_rounds}-day news event cycle.
{environment_context_text(round_ctx.previous_environment)}
The news context is:
{news_state.prompt_context()}
Your previous polarity was: {state.polarity}
Your previous attitude was: {state.attitude.model_dump()}
Your previous emotion was: {state.emotion.model_dump()}
Your attribute characteristics: {profile.characteristic}
Your current state should be updated consistently.

Tasks:
1. Determine the updated polarity for this group: negative, positive, or both.
2. Update the attitude values: optimism, pessimism, neutrality.
3. Update the emotion values: happiness, sadness, anger.
4. Ensure values are between 0 and 1.
5. The outputs should be coherent with the event cycle, previous environment state, and this group's characteristics.
6. If the group is mostly one-sided, keep a small minority attitude possible rather than forcing a perfectly pure state.

Return JSON:
{{
  "polarity": "negative",
  "optimism": 0.0,
  "pessimism": 0.0,
  "neutrality": 0.0,
  "happiness": 0.0,
  "sadness": 0.0,
  "anger": 0.0,
  "reason": ""
}}
"""
        return await self.llm_gateway.complete_json(prompt)

    @staticmethod
    def _parse_polarity(raw_value, fallback: int) -> int:
        polarity = str(raw_value or "").strip().lower()
        if polarity == "positive":
            return 1
        if polarity == "negative":
            return 0
        if polarity == "both":
            return 2
        return fallback if fallback != -1 else 2
