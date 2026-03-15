from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import time

from pydantic import BaseModel, Field

from app.actions.government_intervention import GovernmentIntervention
from app.compat.metagpt import EnvironmentBase, METAGPT_AVAILABLE
from app.roles.group_agent import GroupAgent
from app.schema.news_state import NewsState
from app.schema.simulation import RoundContext, RoundSummary, SimulationResult
from app.services.dynamics import detect_intervention_signal, dominant_sentiment_from_news
from app.services.environment_state import build_environment_state
from app.services.llm import LLMGateway
from app.services.runtime_logging import (
    console_banner,
    console_group_panel,
    console_info,
    console_parallel_status,
    console_phase,
    console_round,
    console_success,
    console_warn,
)


class SimulationEnv(EnvironmentBase, BaseModel):
    description: str = "GA-S3 social simulation environment"
    group_agents: list[GroupAgent] = Field(default_factory=list)
    round_summaries: list[RoundSummary] = Field(default_factory=list)
    group_concurrency: int = 6

    def model_post_init(self, __context) -> None:
        if METAGPT_AVAILABLE:
            self.add_roles(self.group_agents)

    async def run_simulation(self, news_state: NewsState, total_rounds: int, llm_gateway: LLMGateway) -> SimulationResult:
        result = SimulationResult()
        console_banner("GA-S3 Group Agent Social Simulation")
        previous_environment = None
        simulation_started_at = time.perf_counter()

        for round_id in range(1, total_rounds + 1):
            round_started_at = time.perf_counter()
            console_round(f"[Round {round_id}/{total_rounds}] Event propagation start")
            round_ctx = RoundContext(
                current_round=round_id,
                total_rounds=total_rounds,
                previous_environment=previous_environment,
            )
            summary = RoundSummary(round_id=round_id)
            round_news_state = news_state.model_copy(deep=True)

            if round_id >= 2 and detect_intervention_signal(news_state) and not news_state.interventions:
                console_warn(f"[Intervention] round {round_id} official intervention check start")
                intervention_action = GovernmentIntervention(llm_gateway=llm_gateway)
                intervention = await intervention_action.run(news_state, round_ctx)
                console_info(f"[Intervention] round {round_id} result={intervention}")
                round_news_state = news_state.model_copy(deep=True)

            for role in self.group_agents:
                role.group_state.news_comments_updated = bool(round_news_state.comment_threads)
                role.group_state.government_agent_intervene = bool(round_news_state.interventions)

            semaphore = asyncio.Semaphore(max(1, self.group_concurrency))
            console_parallel_status(
                f"[Round {round_id}/{total_rounds}] running {len(self.group_agents)} groups with concurrency={max(1, self.group_concurrency)}"
            )

            async def _run_role(role: GroupAgent):
                async with semaphore:
                    return await role.run_round(round_news_state, round_ctx, llm_gateway)

            group_results = await asyncio.gather(*[_run_role(role) for role in self.group_agents])
            for group_result in sorted(group_results, key=lambda item: (item.layer, item.group_id)):
                console_group_panel(
                    group_name=group_result.group_name or group_result.group_id,
                    group_id=group_result.group_id,
                    hierarchy_path=group_result.hierarchy_path,
                    polarity=group_result.polarity,
                    emotion=group_result.emotion.model_dump(),
                    attitude=group_result.attitude.model_dump(),
                    internal_groups={k: v.model_dump() for k, v in group_result.internal_groups.items()},
                    metrics=group_result.metrics,
                    comment=group_result.comment,
                )
            for group_result in group_results:
                summary.group_results.append(group_result)
                for metric, value in group_result.metrics.items():
                    summary.total_metrics[metric] += value

            for group_result in summary.group_results:
                news_state.append_comment(group_result.comment or "")
                news_state.apply_metrics(group_result.metrics)

            summary.dominant_sentiment = dominant_sentiment_from_news(news_state)
            summary.environment_state = build_environment_state(news_state, summary, total_rounds)
            news_state.round_history.append(summary.model_dump())
            self.round_summaries.append(summary)
            result.rounds.append(summary)
            previous_environment = summary.environment_state
            console_phase("System Dynamics", f"round {round_id} dominant_sentiment={summary.dominant_sentiment}")
            console_info(
                "[Environment] "
                f"heat={summary.environment_state.heat_stage} "
                f"lifecycle={summary.environment_state.event_lifecycle_stage} "
                f"comments={summary.environment_state.comment_climate} "
                f"alignment={summary.environment_state.trend_alignment_score}"
            )
            round_elapsed = time.perf_counter() - round_started_at
            total_elapsed = time.perf_counter() - simulation_started_at
            avg_round = total_elapsed / round_id
            remaining_rounds = total_rounds - round_id
            remaining_seconds = avg_round * remaining_rounds
            eta = datetime.now() + timedelta(seconds=remaining_seconds)
            console_info(
                f"[Timing] round_elapsed={round_elapsed:.2f}s total_elapsed={total_elapsed:.2f}s "
                f"eta={eta.strftime('%H:%M:%S')} remaining≈{remaining_seconds:.2f}s"
            )
            console_success(f"[Round {round_id}/{total_rounds}] global totals={summary.total_metrics}")

        return result
