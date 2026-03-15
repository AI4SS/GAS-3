from __future__ import annotations

from pydantic import BaseModel, Field


class InterventionRecord(BaseModel):
    round_id: int
    actor: str
    action: str
    summary: str


class NewsState(BaseModel):
    news_id: str
    title: str
    content: str
    category: str
    publish_time: str
    source_dataset: str = ""
    event_id: int | None = None
    benchmark_engagement: dict[str, float] = Field(default_factory=dict)
    benchmark_traffic: dict[str, int] = Field(default_factory=dict)
    publisher_id: str = "publisher_1"
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    follows: int = 0
    comment_threads: list[str] = Field(default_factory=list)
    interventions: list[InterventionRecord] = Field(default_factory=list)
    round_history: list[dict] = Field(default_factory=list)

    @property
    def base_content(self) -> str:
        return self.content.split("\ncomment:", 1)[0]

    def recent_comments(self, limit: int = 6) -> list[str]:
        if limit <= 0:
            return []
        return self.comment_threads[-limit:]

    def prompt_context(self, comment_limit: int = 6) -> str:
        parts = [f"Original news content:\n{self.base_content}"]
        if self.comment_threads:
            comments = "\n".join(f"- {comment}" for comment in self.recent_comments(comment_limit))
            parts.append(f"Recent public comments:\n{comments}")
        if self.interventions:
            latest = self.interventions[-1]
            parts.append(
                "Latest official intervention:\n"
                f"- action: {latest.action}\n"
                f"- summary: {latest.summary or 'N/A'}"
            )
        return "\n\n".join(parts)

    def append_comment(self, comment: str) -> None:
        if not comment:
            return
        self.comment_threads.append(comment)
        self.content = f"{self.content}\ncomment: {comment}"

    def apply_metrics(self, metrics: dict[str, int]) -> None:
        self.views += metrics.get("views", 0)
        self.likes += metrics.get("likes", 0)
        self.comments += metrics.get("comments", 0)
        self.shares += metrics.get("shares", 0)
        self.follows += metrics.get("follows", 0)
