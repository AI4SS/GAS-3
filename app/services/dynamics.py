from __future__ import annotations

import re

from app.schema.agent_state import AttitudeState, EmotionState, GroupProfile, GroupState, InternalSubgroup
from app.schema.news_state import InterventionRecord, NewsState
from app.schema.simulation import EnvironmentState, RoundContext


ROUND_INTENSITY = {
    1: 0.22,
    2: 0.35,
    3: 0.62,
    4: 0.55,
    5: 0.33,
    6: 0.18,
    7: 0.1,
}

POSITIVE_HINTS = {
    "cleared",
    "support",
    "improve",
    "apology",
    "respond",
    "announce",
    "promote",
    "launched",
    "record",
    "success",
    "confidence",
    "reform",
    "corrective",
    "improvement",
}
NEGATIVE_HINTS = {
    "misconduct",
    "tampering",
    "fabricating",
    "plagiarism",
    "anger",
    "ban",
    "abuse",
    "scandal",
    "lose",
    "loss",
    "defeat",
    "humiliating",
    "skepticism",
    "spoiled",
    "crashes",
    "fatal",
    "detained",
    "forfeit",
    "resigns",
    "wrong way",
    "dishonesty",
}


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def keyword_score(text: str) -> tuple[float, float]:
    content = text.lower()
    positive = sum(1 for token in POSITIVE_HINTS if token in content)
    negative = sum(1 for token in NEGATIVE_HINTS if token in content)
    return float(positive), float(negative)


def detect_polarity(optimism: float, pessimism: float) -> int:
    if optimism > 0.1 and pessimism > 0.1:
        return 2
    if optimism > pessimism:
        return 1
    if pessimism > optimism:
        return 0
    return 2


def get_attitude_footer_by_polarity(polarity: int) -> str:
    configs = {
        0: {
            "dynamic_instruction": "In a typical news cycle, attitudes tend to fluctuate initially, then stabilize over time.",
            "optimism": 0,
            "pessimism": "()",
            "condition": "pessimism has a value greater than 0 and optimism is 0",
            "additional_clause": "",
        },
        1: {
            "dynamic_instruction": "In a typical news cycle, attitudes tend to fluctuate initially, then stabilize over time.",
            "optimism": "()",
            "pessimism": 0,
            "condition": "optimism has a value greater than 0 and pessimism is 0",
            "additional_clause": "",
        },
        2: {
            "dynamic_instruction": "In a typical news cycle, attitudes tend to fluctuate initially, then stabilize over time.",
            "optimism": "()",
            "pessimism": "()",
            "condition": "both optimism and pessimism have values greater than 0",
            "additional_clause": "",
        },
        3: {
            "dynamic_instruction": "Your attitude polarity remains unchanged, but the intensity should increase compared to the previous value.",
            "optimism": "()",
            "pessimism": "()",
            "condition": "the previous dominant attitude has an increased intensity",
            "additional_clause": " If either optimism or pessimism was previously 0, the updated value must remain 0.",
        },
        4: {
            "dynamic_instruction": "Your attitude polarity remains unchanged, but the intensity should decrease compared to the previous value.",
            "optimism": "()",
            "pessimism": "()",
            "condition": "the previous dominant attitude has a decreased intensity",
            "additional_clause": " If either optimism or pessimism was previously 0, the updated value must remain 0.",
        },
    }
    cfg = configs.get(polarity, configs[2])
    return (
        "1. Based on the news content, along with your current attitudes and attribute characteristics, "
        "consider the current day within the event cycle to update your attitudes.\n"
        f"2. {cfg['dynamic_instruction']}\n"
        "3. Return JSON with keys optimism, pessimism, neutrality and reason.\n"
        f"4. Ensure {cfg['condition']}.{cfg['additional_clause']}"
    )


def get_emotion_footer() -> str:
    return (
        "1. Based on the news content, along with your current emotions, attitudes, and attribute characteristics, "
        "consider the current day within the event cycle to update your emotions.\n"
        "2. In a typical news cycle, emotions initially surge, then decline quickly, and eventually stabilize.\n"
        "3. If the sentiment polarity has changed, the emotional intensity should increase significantly.\n"
        "4. If the sentiment polarity remains the same, the emotional intensity should be lower than the previous emotional intensity.\n"
        "5. Return JSON with keys happiness, sadness, anger and reason."
    )


def environment_context_text(environment: EnvironmentState | None) -> str:
    if environment is None:
        return "No previous-round environment state is available; treat this as the initial outbreak stage."
    return (
        "Previous-round environment state:\n"
        f"- heat_stage: {environment.heat_stage}\n"
        f"- lifecycle_stage: {environment.event_lifecycle_stage}\n"
        f"- dominant_sentiment: {environment.dominant_sentiment}\n"
        f"- comment_climate: {environment.comment_climate}\n"
        f"- intervention_pressure: {environment.intervention_pressure}\n"
        f"- trend_alignment_score: {environment.trend_alignment_score}\n"
        f"- reference_traffic: {environment.reference_traffic}"
    )


def parse_comment(text: str) -> str:
    match = re.search(r"Comment:\s*(.*)", text, re.IGNORECASE | re.DOTALL)
    return (match.group(1) if match else text).strip()


def clamp_state(state: GroupState) -> GroupState:
    state.attitude.optimism = clamp(state.attitude.optimism)
    state.attitude.pessimism = clamp(state.attitude.pessimism)
    state.attitude.neutrality = clamp(state.attitude.neutrality)
    state.emotion.happiness = clamp(state.emotion.happiness)
    state.emotion.sadness = clamp(state.emotion.sadness)
    state.emotion.anger = clamp(state.emotion.anger)
    return state


def build_emotion_state(score_positive: float, score_negative: float, profile: GroupProfile, round_ctx: RoundContext) -> EmotionState:
    base = ROUND_INTENSITY.get(round_ctx.current_round, 0.1) * profile.category.sensitivity
    base *= environment_emotion_multiplier(round_ctx.previous_environment)
    total = max(score_positive + score_negative, 1.0)
    happiness = clamp(base * (score_positive / total))
    anger = clamp(base * (score_negative / total))
    sadness = clamp((anger * 0.7) + (0.1 if score_negative > score_positive else 0.0))
    return EmotionState(happiness=happiness, anger=anger, sadness=sadness)


def build_attitude_state(score_positive: float, score_negative: float, profile: GroupProfile, environment: EnvironmentState | None = None) -> AttitudeState:
    total = max(score_positive + score_negative, 1.0)
    optimism = clamp((score_positive / total) * profile.category.sensitivity)
    pessimism = clamp((score_negative / total) * profile.category.sensitivity)
    if environment is not None:
        if environment.dominant_sentiment == "supportive":
            optimism = clamp(optimism + 0.05)
        elif environment.dominant_sentiment == "contentious":
            pessimism = clamp(pessimism + 0.08)
        if environment.intervention_pressure >= 0.5:
            pessimism = clamp(pessimism + 0.05)
        if environment.comment_climate == "dense":
            pessimism = clamp(pessimism + 0.04)
    neutrality = clamp(1.0 - max(optimism, pessimism) - min(optimism, pessimism) * 0.5)
    return AttitudeState(optimism=optimism, pessimism=pessimism, neutrality=neutrality)


def sync_internal_groups(state: GroupState, population: int) -> None:
    optimism = state.attitude.optimism
    pessimism = state.attitude.pessimism
    total = optimism + pessimism

    if total <= 0:
        state.internal_groups["optimism"] = InternalSubgroup(population=0, intensity=0.0)
        state.internal_groups["pessimism"] = InternalSubgroup(population=0, intensity=0.0)
        return

    seed_population = max(1, int(population * 0.05))
    if optimism <= 0.1 < pessimism:
        state.internal_groups["optimism"] = InternalSubgroup(
            population=seed_population,
            intensity=max(0.08, optimism or 0.08),
        )
        state.internal_groups["pessimism"] = InternalSubgroup(
            population=max(0, population - seed_population),
            intensity=max(pessimism, 0.15),
        )
        return
    if pessimism <= 0.1 < optimism:
        state.internal_groups["optimism"] = InternalSubgroup(
            population=max(0, population - seed_population),
            intensity=max(optimism, 0.15),
        )
        state.internal_groups["pessimism"] = InternalSubgroup(
            population=seed_population,
            intensity=max(0.08, pessimism or 0.08),
        )
        return

    optimism_population = int(population * optimism / total)
    pessimism_population = population - optimism_population
    state.internal_groups["optimism"] = InternalSubgroup(population=optimism_population, intensity=optimism)
    state.internal_groups["pessimism"] = InternalSubgroup(population=pessimism_population, intensity=pessimism)


def rebalance_internal_groups(
    state: GroupState,
    population: int,
    environment: EnvironmentState | None = None,
) -> None:
    optimism_group = state.internal_groups["optimism"]
    pessimism_group = state.internal_groups["pessimism"]

    if optimism_group.population == 0 and pessimism_group.population == 0:
        sync_internal_groups(state, population)
        optimism_group = state.internal_groups["optimism"]
        pessimism_group = state.internal_groups["pessimism"]

    seed_population = max(1, int(population * 0.05))
    if state.polarity == 0 and optimism_group.population == 0 and state.attitude.pessimism >= 0.45:
        optimism_group.population = seed_population
        optimism_group.intensity = max(0.08, state.attitude.optimism or 0.08)
        pessimism_group.population = max(0, population - optimism_group.population)
        pessimism_group.intensity = max(pessimism_group.intensity, state.attitude.pessimism)
    elif state.polarity == 1 and pessimism_group.population == 0 and state.attitude.optimism >= 0.45:
        pessimism_group.population = seed_population
        pessimism_group.intensity = max(0.08, state.attitude.pessimism or 0.08)
        optimism_group.population = max(0, population - pessimism_group.population)
        optimism_group.intensity = max(optimism_group.intensity, state.attitude.optimism)

    if environment is not None and environment.comment_climate == "dense":
        if optimism_group.population == 0 and state.attitude.optimism > 0.02:
            optimism_group.population = seed_population
            optimism_group.intensity = max(optimism_group.intensity, state.attitude.optimism)
        if pessimism_group.population == 0 and state.attitude.pessimism > 0.02:
            pessimism_group.population = seed_population
            pessimism_group.intensity = max(pessimism_group.intensity, state.attitude.pessimism)

    total = optimism_group.population + pessimism_group.population
    if total > population:
        overflow = total - population
        if optimism_group.population >= pessimism_group.population:
            optimism_group.population = max(0, optimism_group.population - overflow)
        else:
            pessimism_group.population = max(0, pessimism_group.population - overflow)
    elif total < population:
        gap = population - total
        if state.attitude.pessimism >= state.attitude.optimism:
            pessimism_group.population += gap
        else:
            optimism_group.population += gap


def aggregate_attitude_from_subgroups(state: GroupState, population: int) -> None:
    if population <= 0:
        return
    optimism_group = state.internal_groups["optimism"]
    pessimism_group = state.internal_groups["pessimism"]
    optimism = clamp((optimism_group.population / population) * optimism_group.intensity)
    pessimism = clamp((pessimism_group.population / population) * pessimism_group.intensity)
    neutrality = clamp(1.0 - optimism - pessimism)
    state.attitude.optimism = optimism
    state.attitude.pessimism = pessimism
    state.attitude.neutrality = neutrality
    state.polarity = detect_polarity(optimism, pessimism)


def adjust_internal_groups_from_feedback(
    state: GroupState,
    news_state: NewsState,
    population: int,
    environment: EnvironmentState | None = None,
) -> None:
    rebalance_internal_groups(state, population, environment)

    comment_bias = sum(1 for c in news_state.comment_threads[-6:] if any(t in c.lower() for t in NEGATIVE_HINTS))
    comment_support = sum(1 for c in news_state.comment_threads[-6:] if any(t in c.lower() for t in POSITIVE_HINTS))
    intervention_effect = 0.0
    if news_state.interventions:
        latest = news_state.interventions[-1].action.lower()
        if latest == "ban":
            intervention_effect = -0.1
        elif latest in {"announce", "respond", "refute"}:
            intervention_effect = 0.06
        elif latest == "promote":
            intervention_effect = 0.1

    climate_effect = 0.0
    if environment is not None:
        if environment.comment_climate == "dense":
            climate_effect -= 0.03
        if environment.dominant_sentiment == "supportive":
            climate_effect += 0.03
        elif environment.dominant_sentiment == "contentious":
            climate_effect -= 0.04

    signal = clamp((comment_support - comment_bias) * 0.03 + intervention_effect + climate_effect, -0.18, 0.18)
    optimism_group = state.internal_groups["optimism"]
    pessimism_group = state.internal_groups["pessimism"]

    total_active = optimism_group.population + pessimism_group.population
    migration_pool = max(1, int(total_active * min(0.22, abs(signal) * 0.75))) if total_active > 0 else 0
    if signal > 0:
        moved = min(migration_pool, pessimism_group.population)
        pessimism_group.population -= moved
        optimism_group.population += moved
    elif signal < 0:
        moved = min(migration_pool, optimism_group.population)
        optimism_group.population -= moved
        pessimism_group.population += moved

    intensity_boost = 0.08
    if environment is not None:
        if environment.heat_stage == "explosive":
            intensity_boost += 0.05
        elif environment.heat_stage == "hot":
            intensity_boost += 0.02
        if environment.intervention_pressure >= 0.5:
            intensity_boost += 0.03

    optimism_group.intensity = clamp(optimism_group.intensity + signal * intensity_boost)
    pessimism_group.intensity = clamp(pessimism_group.intensity - signal * intensity_boost)
    aggregate_attitude_from_subgroups(state, population)


def infer_online_ratio(
    profile: GroupProfile,
    state: GroupState,
    round_ctx: RoundContext,
    benchmark_traffic: dict[str, int] | None = None,
) -> float:
    round_weight = ROUND_INTENSITY.get(round_ctx.current_round, 0.1)
    base_ratio = 0.01 + (round_weight * 0.06 * profile.category.sensitivity)
    base_ratio *= environment_online_multiplier(round_ctx.previous_environment)

    if benchmark_traffic:
        benchmark_value = benchmark_traffic.get(f"day{round_ctx.current_round}", 0)
        if benchmark_value > 0 and profile.population > 0:
            benchmark_ratio = min(0.95, benchmark_value / profile.population)
            base_ratio = (base_ratio * 0.7) + (benchmark_ratio * 0.3)

    return clamp(base_ratio, 0.002, 0.95)


def quantize_metrics_from_ratio(
    profile: GroupProfile,
    state: GroupState,
    round_ctx: RoundContext,
    online_ratio: float,
) -> dict[str, int]:
    views = int(profile.population * online_ratio)

    engagement_drive = clamp(
        0.35 * state.attitude.optimism
        + 0.45 * state.attitude.pessimism
        + 0.20 * (state.emotion.anger + state.emotion.happiness)
    )
    comments_rate = clamp(0.003 + 0.06 * state.attitude.pessimism + 0.04 * state.emotion.anger, 0.002, 0.16)
    likes_rate = clamp(0.01 + 0.08 * state.attitude.optimism + 0.03 * state.emotion.happiness, 0.005, 0.18)
    shares_rate = clamp(0.002 + 0.02 * engagement_drive + 0.015 * state.attitude.pessimism, 0.001, 0.08)
    follows_rate = clamp(0.001 + 0.012 * state.attitude.optimism, 0.0, 0.04)

    if round_ctx.previous_environment is not None:
        env = round_ctx.previous_environment
        if env.comment_climate == "dense":
            comments_rate = clamp(comments_rate * 1.15, 0.002, 0.18)
            shares_rate = clamp(shares_rate * 1.08, 0.001, 0.09)
        if env.heat_stage == "explosive":
            comments_rate = clamp(comments_rate * 1.12, 0.002, 0.2)
            likes_rate = clamp(likes_rate * 1.1, 0.005, 0.2)
        if env.event_lifecycle_stage == "long-tail decay":
            likes_rate *= 0.88
            comments_rate *= 0.82

    likes = int(views * likes_rate)
    comments = int(views * comments_rate)
    shares = int(views * shares_rate)
    follows = int(views * follows_rate)

    if likes >= views:
        likes = max(1, views // 10)
    if comments >= likes:
        comments = max(0, int(likes * 0.75))
    if shares >= likes:
        shares = max(0, int(likes * 0.55))

    return {
        "views": max(0, views),
        "likes": max(0, likes),
        "comments": max(0, comments),
        "shares": max(0, shares),
        "follows": max(0, follows),
    }


def estimate_metrics(profile: GroupProfile, state: GroupState, round_ctx: RoundContext) -> dict[str, int]:
    online_ratio = infer_online_ratio(profile, state, round_ctx)
    return quantize_metrics_from_ratio(profile, state, round_ctx, online_ratio)


def environment_emotion_multiplier(environment: EnvironmentState | None) -> float:
    if environment is None:
        return 1.0
    multiplier = 1.0
    if environment.heat_stage == "explosive":
        multiplier += 0.2
    elif environment.heat_stage == "hot":
        multiplier += 0.1
    if environment.comment_climate == "dense":
        multiplier += 0.08
    if environment.intervention_pressure >= 0.5:
        multiplier += 0.05
    return multiplier


def environment_online_multiplier(environment: EnvironmentState | None) -> float:
    if environment is None:
        return 1.0
    multiplier = 1.0
    if environment.heat_stage == "explosive":
        multiplier += 0.45
    elif environment.heat_stage == "hot":
        multiplier += 0.2
    if environment.event_lifecycle_stage == "rapid diffusion":
        multiplier += 0.1
    elif environment.event_lifecycle_stage == "peak attention":
        multiplier += 0.18
    elif environment.event_lifecycle_stage == "long-tail decay":
        multiplier -= 0.12
    if environment.comment_climate == "dense":
        multiplier += 0.06
    return max(0.65, multiplier)


def detect_intervention_signal(news_state: NewsState) -> bool:
    content = news_state.content.lower()
    return any(token in content for token in {"ban", "announce", "respond", "promote", "refute", "misconduct", "rumor"})


def apply_intervention(news_state: NewsState, intervention: InterventionRecord) -> None:
    news_state.interventions.append(intervention)
    if intervention.summary:
        news_state.content = f"{intervention.action.upper()}: {news_state.content}\n{intervention.summary}"
    else:
        news_state.content = f"{intervention.action.upper()}: {news_state.content}"


def infer_trend_label(news_state: NewsState) -> tuple[str, int]:
    total_engagement = news_state.views + news_state.likes + news_state.comments + news_state.shares
    if total_engagement > 1_000_000:
        return "explosive trending", 2
    if total_engagement > 100_000:
        return "hot trending", 1
    return "ordinary trending", 3


def dominant_sentiment_from_news(news_state: NewsState) -> str:
    if news_state.likes > news_state.comments:
        return "supportive"
    if news_state.comments > news_state.likes:
        return "contentious"
    return "mixed"
