from __future__ import annotations

import csv
import json
from pathlib import Path

from app.schema.news_state import NewsState
from app.schema.simulation import SimulationResult


def persist_results(output_dir: Path, result: SimulationResult, news_state: NewsState) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "simulation_result.json").write_text(
        result.model_dump_json(indent=2),
    )
    (output_dir / "news_state.json").write_text(
        news_state.model_dump_json(indent=2),
    )

    csv_path = output_dir / "traffic_metrics.csv"
    with csv_path.open("w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["round", "views", "likes", "comments", "shares", "follows"])
        writer.writeheader()
        for round_summary in result.rounds:
            writer.writerow({"round": round_summary.round_id, **round_summary.total_metrics})

    (output_dir / "summary.json").write_text(
        json.dumps(
            {
                "total_rounds": len(result.rounds),
                "event_id": news_state.event_id,
                "dataset": news_state.source_dataset,
                "title": news_state.title,
                "category": news_state.category,
                "final_totals": {
                    "views": news_state.views,
                    "likes": news_state.likes,
                    "comments": news_state.comments,
                    "shares": news_state.shares,
                    "follows": news_state.follows,
                },
                "benchmark_traffic": news_state.benchmark_traffic,
            },
            indent=2,
        )
    )
