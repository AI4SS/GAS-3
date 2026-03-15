from __future__ import annotations

from app.schema.agent_state import GroupProfile, PopulationCategory
from app.schema.news_state import NewsState


def build_sample_news() -> NewsState:
    return NewsState(
        news_id="news_1",
        title="Investigation and Handling of Academic Misconduct by Teacher at Huazhong Agricultural University",
        content=(
            "On January 16, 2024, netizens revealed a report letter signed by multiple students from "
            "Huazhong Agricultural University, accusing their supervisor, Professor Huang Feiruo, of "
            "academic misconduct such as data tampering and fabricating experimental results. "
            "On February 6, 2024, the university confirmed the misconduct, terminated the employment "
            "contract, and withdrew papers related to the case."
        ),
        category="Education",
        publish_time="2024-04-17",
    )


def build_sample_groups() -> list[GroupProfile]:
    return [
        GroupProfile(
            id="student_root",
            name="Student Group",
            description="Representing 57 million Chinese students reacting to academic news.",
            identity="Chinese students",
            population=57_000_000,
            characteristic="Susceptible",
            category=PopulationCategory.SUSCEPTIBLE,
        ),
        GroupProfile(
            id="teacher_root",
            name="Teacher Group",
            description="Representing 3.5 million Chinese teachers reacting to academic news.",
            identity="Chinese teachers",
            population=3_500_000,
            characteristic="Calm",
            category=PopulationCategory.CALM,
        ),
    ]
