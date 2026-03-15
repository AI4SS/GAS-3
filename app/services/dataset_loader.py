from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from app.schema.news_state import NewsState


class DatasetEvent(BaseModel):
    id: int
    title: str
    content: str
    engagement_data: dict[str, float] = Field(default_factory=dict)
    network_traffic_variations: dict[str, int] = Field(default_factory=dict)


def load_dataset_events(dataset_path: Path) -> list[DatasetEvent]:
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    events: list[DatasetEvent] = []
    for item in payload:
        events.append(
            DatasetEvent(
                id=int(item["id"]),
                title=str(item["title"]),
                content=str(item["content"]),
                engagement_data={str(k): float(v) for k, v in item.get("Engagement Data", {}).items()},
                network_traffic_variations={
                    str(k): int(float(v)) for k, v in item.get("Network Traffic Variations", {}).items()
                },
            )
        )
    return events


def select_dataset_event(events: list[DatasetEvent], event_id: int | None = None) -> DatasetEvent:
    if not events:
        raise ValueError("No events loaded from dataset.")
    if event_id is None:
        return events[0]
    for event in events:
        if event.id == event_id:
            return event
    raise ValueError(f"Event id {event_id} not found in dataset.")


def build_news_state_from_event(event: DatasetEvent, dataset_name: str = "benchmark") -> NewsState:
    return NewsState(
        news_id=f"news_{event.id}",
        event_id=event.id,
        title=event.title,
        content=event.content,
        category=infer_category_from_text(event.title, event.content),
        publish_time="2024-01-01",
        source_dataset=dataset_name,
        benchmark_engagement=event.engagement_data,
        benchmark_traffic=event.network_traffic_variations,
    )


def infer_category_from_text(title: str, content: str) -> str:
    lowered = f"{title} {content}".lower()
    if any(token in lowered for token in {"professor", "university", "student", "academic", "school"}):
        return "Education"
    if any(token in lowered for token in {"football", "basketball", "match", "team", "sports"}):
        return "Sports"
    if any(token in lowered for token in {"game", "steam", "playstation"}):
        return "Entertainment"
    if any(token in lowered for token in {"retirement", "workers", "welfare", "policy"}):
        return "Policy"
    return "Social"
