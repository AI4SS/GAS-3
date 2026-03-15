from __future__ import annotations

from app.compat.metagpt import ActionBase
from app.schema.agent_state import GroupProfile, GroupState
from app.schema.news_state import NewsState
from app.schema.simulation import RoundContext
from app.services.dynamics import environment_context_text, parse_comment
from app.services.llm import LLMGateway


class GenerateComment(ActionBase):
    async def run(
        self,
        profile: GroupProfile,
        state: GroupState,
        news_state: NewsState,
        round_ctx: RoundContext,
        llm_gateway: LLMGateway | None = None,
    ) -> str:
        if llm_gateway:
            llm_comment = await self._request_comment(profile, state, news_state, round_ctx, llm_gateway)
            if llm_comment:
                return parse_comment(llm_comment)

        if state.attitude.pessimism >= state.attitude.optimism:
            tone = "questions the handling and demands stronger accountability"
        else:
            tone = "focuses on corrective action and hopes for institutional improvement"
        if round_ctx.previous_environment and round_ctx.previous_environment.heat_stage in {"hot", "explosive"}:
            tone += " amid intensified public attention"

        return (
            f"As {profile.identity} focused on {profile.focus_label}, this group {tone} in round {round_ctx.current_round} "
            f"after reading '{news_state.title}'."
        )

    async def _request_comment(
        self,
        profile: GroupProfile,
        state: GroupState,
        news_state: NewsState,
        round_ctx: RoundContext,
        llm_gateway: LLMGateway,
    ) -> str | None:
        footer = """
1. Based on the news content and the current day within the event cycle, please comment based on your current emotions and attitudes.
2. Use the perspective of your group and identity to support, criticize, or question news content in an emotionally appropriate way.
3. Your comment should be aligned with your assigned polarity (0 is Pessimism, 1 is optimism, 2 is both).
4. Comments should simulate real human comments, express opinions in one sentence as concisely as possible, and avoid being lengthy.
5. Your responses must follow this template:
Comment:
"""
        prompt = f"""
You are {profile.name}, {profile.description}.
Your hierarchy path is: {' > '.join(profile.hierarchy_path) or profile.name}.
Your subgroup focus is: {profile.focus_label}. Related keywords: {profile.focus_keywords}.
Your current emotion is: {state.emotion.model_dump()}
Your current attitude is: {state.attitude.model_dump()}
The current sentiment polarity is: {state.polarity}
You are situated within a simulated environment characterized by the following properties: Academic Social Network.
This is Day {round_ctx.current_round} of a {round_ctx.total_rounds}-day news event cycle.
{environment_context_text(round_ctx.previous_environment)}
The news context you have received is:
{news_state.prompt_context()}

{footer}
"""
        return await llm_gateway.complete_text(prompt)
