from __future__ import annotations

import asyncio
from pathlib import Path

from app.compat.metagpt import METAGPT_AVAILABLE, METAGPT_IMPORT_ERROR, config
from app.environment.simulation_env import SimulationEnv
from app.roles.group_agent import GroupAgent
from app.services.config import load_settings
from app.services.dataset_loader import build_news_state_from_event, load_dataset_events, select_dataset_event
from app.services.hierarchy import build_hierarchical_groups
from app.services.llm import LLMGateway
from app.services.persistence import persist_results
from app.services.runtime_logging import BLUE, console_banner, console_info, console_phase, init_log_dir
from app.services.sample_data import build_sample_groups


async def async_main() -> None:
    settings = load_settings()
    events = load_dataset_events(Path(settings.runtime.dataset_path))
    selected_event = select_dataset_event(events, settings.runtime.event_id)
    output_dir = Path(settings.runtime.results_dir) / f"event_{selected_event.id}"
    init_log_dir(str(output_dir))
    console_banner("MetaGPT Refactored GA-S3 Runner")
    console_info(
        f"[Main] start use_llm={settings.runtime.use_llm} "
        f"model={settings.llm.model} base_url={settings.llm.base_url} rounds={settings.runtime.total_rounds}",
        color=BLUE,
    )

    if hasattr(config, "update_via_dict"):
        config.update_via_dict(
            {
                "llm": {
                    "api_type": settings.llm.api_type,
                    "base_url": settings.llm.base_url,
                    "api_key": settings.llm.api_key,
                    "model": settings.llm.model,
                }
            }
        )

    llm_gateway = LLMGateway(settings.llm, enabled=settings.runtime.use_llm)
    news_state = build_news_state_from_event(selected_event)
    console_info(
        f"[Dataset] source={news_state.source_dataset} event_id={selected_event.id} category={news_state.category} title={news_state.title}",
        color=BLUE,
    )
    console_phase("Hierarchical Generation", f"building group hierarchy for category={news_state.category}")
    try:
        hierarchy_plan = await build_hierarchical_groups(
            news_state,
            llm_gateway,
            output_dir / "cache",
        )
        active_profiles = hierarchy_plan.leaf_groups or build_sample_groups()
        console_info(
            f"[Hierarchy] nodes={len(hierarchy_plan.tree_nodes)} active_leaf_groups={len(active_profiles)}",
            color=BLUE,
        )
    except Exception as exc:
        active_profiles = build_sample_groups()
        console_info(f"[Hierarchy] fallback to predefined groups due to: {exc}", color=BLUE)
    agents = [GroupAgent(group_profile=profile) for profile in active_profiles]
    env = SimulationEnv(group_agents=agents, group_concurrency=settings.runtime.group_concurrency)

    result = await env.run_simulation(news_state, settings.runtime.total_rounds, llm_gateway)
    persist_results(output_dir, result, news_state)

    print(f"MetaGPT available: {METAGPT_AVAILABLE}")
    if not METAGPT_AVAILABLE:
        print(f"MetaGPT import error: {METAGPT_IMPORT_ERROR}")
    print(f"Simulation finished with {len(result.rounds)} rounds.")
    print(f"Final totals: views={news_state.views}, likes={news_state.likes}, comments={news_state.comments}")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
