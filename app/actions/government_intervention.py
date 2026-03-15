from __future__ import annotations

import re

from pydantic import ConfigDict

from app.compat.metagpt import ActionBase
from app.schema.news_state import InterventionRecord, NewsState
from app.schema.simulation import RoundContext
from app.services.dynamics import apply_intervention
from app.services.llm import LLMGateway


class GovernmentIntervention(ActionBase):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    llm_gateway: LLMGateway | None = None

    async def run(self, news_state: NewsState, round_ctx: RoundContext) -> InterventionRecord | None:
        llm_result = await self._request_intervention(news_state, round_ctx)
        if llm_result:
            record = InterventionRecord(
                round_id=round_ctx.current_round,
                actor="government_agent",
                action=str(llm_result.get("action", "none")).lower(),
                summary=str(llm_result.get("extracted_content", "") or llm_result.get("reason", "")),
            )
        else:
            record = self._heuristic_intervention(news_state, round_ctx.current_round)

        if record.action == "none":
            return None

        apply_intervention(news_state, record)
        return record

    async def _request_intervention(self, news_state: NewsState, round_ctx: RoundContext) -> dict | None:
        if not self.llm_gateway:
            return None
        prompt = f"""
You are Government Agent in Academic Social Network.
This is Day {round_ctx.current_round} of a {round_ctx.total_rounds}-day news event cycle.
The news context you have received is:
{news_state.prompt_context()}

1. Analyze the news content and its potential impact on society.
2. Based on the news content and its keywords, select one action:
   ban / announce / respond / promote / refute / none
3. If the action is announce, respond, or refute, extract the relevant part of the news content.
4. Return JSON:
{{
  "action": "ban",
  "reason": "",
  "extracted_content": ""
}}
"""
        response = await self.llm_gateway.complete_json(prompt)
        if response and str(response.get("action", "")).lower() in {"ban", "announce", "respond", "promote", "refute", "none"}:
            return response
        return None

    def _heuristic_intervention(self, news_state: NewsState, current_round: int) -> InterventionRecord:
        lowered = news_state.content.lower()
        if "rumor" in lowered:
            action = "refute"
        elif "misconduct" in lowered or "plagiarism" in lowered:
            action = "announce"
        elif re.search(r"\briot|violent|panic\b", lowered):
            action = "ban"
        else:
            action = "none"
        return InterventionRecord(
            round_id=current_round,
            actor="government_agent",
            action=action,
            summary="Official response inserted into the news context." if action != "none" else "",
        )
