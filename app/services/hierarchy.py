from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, Field

from app.schema.agent_state import GroupProfile, PopulationCategory
from app.schema.news_state import NewsState
from app.services.llm import LLMGateway


class HierarchyPlan(BaseModel):
    tree_nodes: list[GroupProfile] = Field(default_factory=list)
    leaf_groups: list[GroupProfile] = Field(default_factory=list)


@dataclass
class ParsedHierarchyNode:
    level: int
    name: str
    population: int
    children: list["ParsedHierarchyNode"] = field(default_factory=list)


async def build_hierarchical_groups(
    news_state: NewsState,
    llm_gateway: LLMGateway | None = None,
    cache_dir: Path | None = None,
) -> HierarchyPlan:
    cached_plan = _load_cached_hierarchy(news_state, cache_dir)
    if cached_plan is not None:
        return cached_plan
    if llm_gateway and llm_gateway.enabled:
        plan = await _build_hierarchy_via_llm(news_state, llm_gateway)
        if plan and plan.leaf_groups:
            _save_hierarchy_cache(news_state, plan, cache_dir)
            return plan
    return _build_rule_based_hierarchy(news_state)


def _build_rule_based_hierarchy(news_state: NewsState) -> HierarchyPlan:
    category = news_state.category.lower()
    keywords = _extract_event_keywords(news_state)

    if category == "education":
        return _education_hierarchy(keywords)
    if category == "sports":
        return _sports_hierarchy(keywords)
    if category == "entertainment":
        return _entertainment_hierarchy(keywords)
    if category == "policy":
        return _policy_hierarchy(keywords)
    return _social_hierarchy(keywords)


async def _build_hierarchy_via_llm(news_state: NewsState, llm_gateway: LLMGateway) -> HierarchyPlan | None:
    prompt = _hierarchy_prompt(news_state)
    system_prompt = (
        "You generate hierarchical population group structures for simulation. "
        "Output only the hierarchy in the requested markdown format."
    )
    text = await llm_gateway.complete_text(prompt, system_prompt=system_prompt)
    if not text:
        return None
    return _parse_hierarchy_response(text, news_state)


def _education_hierarchy(keywords: list[str]) -> HierarchyPlan:
    nodes: list[GroupProfile] = []
    leaves: list[GroupProfile] = []

    root_students = _node(
        "education_students_root",
        "Student Community Cluster",
        "Chinese university students",
        45_000_000,
        "Susceptible",
        PopulationCategory.SUSCEPTIBLE,
        "L1",
        None,
        "student response",
        keywords,
    )
    root_parents = _node(
        "education_parents_root",
        "Parent Community Cluster",
        "Chinese parents of college students",
        32_000_000,
        "Average",
        PopulationCategory.AVERAGE,
        "L1",
        None,
        "parent response",
        keywords,
    )
    root_professionals = _node(
        "education_professionals_root",
        "Education Professional Cluster",
        "Chinese education professionals",
        12_000_000,
        "Calm",
        PopulationCategory.CALM,
        "L1",
        None,
        "professional response",
        keywords,
    )
    nodes.extend([root_students, root_parents, root_professionals])

    student_focuses = [
        ("education_students_integrity", "Academic Integrity Concern Group", 0.55, "academic integrity", ["integrity", "misconduct", "plagiarism"]),
        ("education_students_fairness", "Student Fairness Concern Group", 0.45, "student fairness", ["fairness", "supervisor", "whistleblower"]),
    ]
    parent_focuses = [
        ("education_parents_safety", "Parental Trust and Safety Group", 0.5, "student protection", ["trust", "protection", "campus"]),
        ("education_parents_accountability", "Parental Accountability Group", 0.5, "institutional accountability", ["accountability", "investigation", "reform"]),
    ]
    professional_focuses = [
        ("education_professionals_ethics", "Research Ethics Group", 0.6, "research ethics", ["research ethics", "papers", "data"]),
        ("education_professionals_governance", "Academic Governance Group", 0.4, "institutional governance", ["governance", "supervision", "institution"]),
    ]

    leaves.extend(_children(root_students, student_focuses))
    leaves.extend(_children(root_parents, parent_focuses))
    leaves.extend(_children(root_professionals, professional_focuses))
    nodes.extend(leaves)
    return HierarchyPlan(tree_nodes=nodes, leaf_groups=leaves)


def _sports_hierarchy(keywords: list[str]) -> HierarchyPlan:
    nodes, leaves = _generic_hierarchy(
        roots=[
            ("sports_fans_root", "Sports Fans Cluster", "Chinese sports fans", 58_000_000, "Susceptible", PopulationCategory.SUSCEPTIBLE),
            ("sports_commentators_root", "Sports Commentator Cluster", "Chinese sports commentators", 4_000_000, "Average", PopulationCategory.AVERAGE),
            ("sports_admins_root", "Sports Administration Cluster", "Chinese sports administrators", 1_200_000, "Calm", PopulationCategory.CALM),
        ],
        focus_map={
            "sports_fans_root": [
                ("sports_fans_emotional", "Emotional Reaction Group", 0.6, "emotional reaction", ["loss", "win", "humiliation"]),
                ("sports_fans_identity", "National Identity Group", 0.4, "collective identity", ["national team", "honor", "reputation"]),
            ],
            "sports_commentators_root": [
                ("sports_commentators_tactics", "Tactical Analysis Group", 0.5, "tactical analysis", ["skills", "tactics", "performance"]),
                ("sports_commentators_reform", "Reform Discussion Group", 0.5, "institutional reform", ["reform", "system", "management"]),
            ],
            "sports_admins_root": [
                ("sports_admins_governance", "Sports Governance Group", 0.6, "governance response", ["governance", "administration", "institution"]),
                ("sports_admins_development", "Talent Development Group", 0.4, "talent development", ["training", "youth", "pipeline"]),
            ],
        },
        keywords=keywords,
    )
    return HierarchyPlan(tree_nodes=nodes, leaf_groups=leaves)


def _entertainment_hierarchy(keywords: list[str]) -> HierarchyPlan:
    nodes, leaves = _generic_hierarchy(
        roots=[
            ("entertainment_players_root", "Core Player Cluster", "Chinese core gamers", 28_000_000, "Susceptible", PopulationCategory.SUSCEPTIBLE),
            ("entertainment_general_root", "General Audience Cluster", "Chinese entertainment audience", 40_000_000, "Average", PopulationCategory.AVERAGE),
            ("entertainment_industry_root", "Industry Observer Cluster", "Chinese culture industry observers", 3_000_000, "Calm", PopulationCategory.CALM),
        ],
        focus_map={
            "entertainment_players_root": [
                ("entertainment_players_gameplay", "Gameplay Experience Group", 0.55, "gameplay response", ["gameplay", "launch", "sales"]),
                ("entertainment_players_identity", "Cultural Confidence Group", 0.45, "cultural identity", ["mythology", "culture", "confidence"]),
            ],
            "entertainment_general_root": [
                ("entertainment_general_popularity", "Public Attention Group", 0.6, "mass popularity", ["attention", "market", "public opinion"]),
                ("entertainment_general_culture", "Cultural Symbolism Group", 0.4, "cultural symbolism", ["culture", "image", "modern China"]),
            ],
            "entertainment_industry_root": [
                ("entertainment_industry_market", "Market Observation Group", 0.5, "market analysis", ["revenue", "sales", "industry"]),
                ("entertainment_industry_strategy", "Strategic Expansion Group", 0.5, "industry strategy", ["global", "platform", "brand"]),
            ],
        },
        keywords=keywords,
    )
    return HierarchyPlan(tree_nodes=nodes, leaf_groups=leaves)


def _policy_hierarchy(keywords: list[str]) -> HierarchyPlan:
    nodes, leaves = _generic_hierarchy(
        roots=[
            ("policy_workers_root", "Working Population Cluster", "Chinese workers", 180_000_000, "Average", PopulationCategory.AVERAGE),
            ("policy_retirees_root", "Near-Retirement Cluster", "Chinese near-retirement citizens", 48_000_000, "Susceptible", PopulationCategory.SUSCEPTIBLE),
            ("policy_experts_root", "Policy Analyst Cluster", "Chinese policy analysts", 2_500_000, "Calm", PopulationCategory.CALM),
        ],
        focus_map={
            "policy_workers_root": [
                ("policy_workers_income", "Income and Career Group", 0.55, "income pressure", ["income", "work", "career"]),
                ("policy_workers_security", "Labor Security Group", 0.45, "labor security", ["welfare", "pension", "security"]),
            ],
            "policy_retirees_root": [
                ("policy_retirees_fairness", "Retirement Fairness Group", 0.5, "retirement fairness", ["retirement age", "fairness", "burden"]),
                ("policy_retirees_family", "Family Welfare Group", 0.5, "family welfare", ["elderly welfare", "family", "support"]),
            ],
            "policy_experts_root": [
                ("policy_experts_design", "Policy Design Group", 0.6, "policy design", ["implementation", "transition", "policy"]),
                ("policy_experts_macros", "Macro Labor Group", 0.4, "macro labor structure", ["labor", "population", "demography"]),
            ],
        },
        keywords=keywords,
    )
    return HierarchyPlan(tree_nodes=nodes, leaf_groups=leaves)


def _social_hierarchy(keywords: list[str]) -> HierarchyPlan:
    nodes, leaves = _generic_hierarchy(
        roots=[
            ("social_public_root", "General Public Cluster", "Chinese general public", 95_000_000, "Average", PopulationCategory.AVERAGE),
            ("social_affected_root", "Affected Community Cluster", "closely affected community members", 18_000_000, "Susceptible", PopulationCategory.SUSCEPTIBLE),
            ("social_observers_root", "Institutional Observer Cluster", "institutional observers", 3_000_000, "Calm", PopulationCategory.CALM),
        ],
        focus_map={
            "social_public_root": [
                ("social_public_moral", "Moral Judgment Group", 0.5, "moral judgment", ["responsibility", "norms", "public reaction"]),
                ("social_public_attention", "Attention Amplification Group", 0.5, "attention amplification", ["viral", "discussion", "traffic"]),
            ],
            "social_affected_root": [
                ("social_affected_safety", "Direct Safety Concern Group", 0.55, "direct safety", ["safety", "harm", "victim"]),
                ("social_affected_accountability", "Direct Accountability Group", 0.45, "direct accountability", ["accountability", "response", "justice"]),
            ],
            "social_observers_root": [
                ("social_observers_governance", "Governance Review Group", 0.6, "governance review", ["governance", "regulation", "institution"]),
                ("social_observers_reform", "Policy Reform Group", 0.4, "system reform", ["reform", "policy", "system"]),
            ],
        },
        keywords=keywords,
    )
    return HierarchyPlan(tree_nodes=nodes, leaf_groups=leaves)


def _generic_hierarchy(
    roots: list[tuple[str, str, str, int, str, PopulationCategory]],
    focus_map: dict[str, list[tuple[str, str, float, str, list[str]]]],
    keywords: list[str],
) -> tuple[list[GroupProfile], list[GroupProfile]]:
    nodes: list[GroupProfile] = []
    leaves: list[GroupProfile] = []
    for root_id, root_name, identity, population, characteristic, category in roots:
        root = _node(root_id, root_name, identity, population, characteristic, category, "L1", None, root_name.lower(), keywords)
        nodes.append(root)
        children = _children(root, focus_map[root_id])
        nodes.extend(children)
        leaves.extend(children)
    return nodes, leaves


def _children(
    parent: GroupProfile,
    definitions: list[tuple[str, str, float, str, list[str]]],
) -> list[GroupProfile]:
    children: list[GroupProfile] = []
    for child_id, child_name, ratio, focus_label, focus_keywords in definitions:
        population = int(parent.population * ratio)
        characteristic = parent.characteristic
        category = parent.category
        children.append(
            GroupProfile(
                id=child_id,
                name=child_name,
                description=(
                    f"Representing {population:,} {parent.identity} focused on {focus_label} "
                    f"while reacting to the current event."
                ),
                identity=parent.identity,
                population=population,
                characteristic=characteristic,
                layer="L2",
                parent_id=parent.id,
                hierarchy_path=[parent.name, child_name],
                focus_label=focus_label,
                focus_keywords=focus_keywords,
                category=category,
            )
        )
    return children


def _node(
    node_id: str,
    name: str,
    identity: str,
    population: int,
    characteristic: str,
    category: PopulationCategory,
    layer: str,
    parent_id: str | None,
    focus_label: str,
    keywords: list[str],
) -> GroupProfile:
    return GroupProfile(
        id=node_id,
        name=name,
        description=f"Representing {population:,} {identity} reacting to the current event.",
        identity=identity,
        population=population,
        characteristic=characteristic,
        layer=layer,
        parent_id=parent_id,
        hierarchy_path=[name],
        focus_label=focus_label,
        focus_keywords=keywords,
        category=category,
    )


def _extract_event_keywords(news_state: NewsState, limit: int = 8) -> list[str]:
    lowered = f"{news_state.title} {news_state.content}".lower()
    candidates = [
        "misconduct",
        "academic",
        "integrity",
        "plagiarism",
        "football",
        "basketball",
        "reform",
        "retirement",
        "policy",
        "game",
        "culture",
        "safety",
        "airport",
        "school",
        "university",
        "fraud",
        "students",
        "parents",
    ]
    hits = [keyword for keyword in candidates if keyword in lowered]
    return hits[:limit] or [news_state.category.lower()]


def _hierarchy_prompt(news_state: NewsState) -> str:
    return f"""
Instructions:
You are an AI assistant specializing in generating hierarchical population group structures based
on the provided country and domain. Use the given context to create a detailed tree-structured
hierarchy that includes group names and corresponding numbers at each level.

Domain: {news_state.category}
Country: CN
Event title: {news_state.title}
Event summary:
{news_state.base_content}

Your task is to generate a multi-level hierarchy for population groups, adjusting the structure
based on the country and domain. Use the following format:
- First Layer (Domain-level Groups, denoted by ##):
Broad categories representing the major population groups of the domain in the given field.
- Second Layer (Subgroups, denoted by 1. ** **):
Specific subdivisions of each first-layer group.
- Third Layer (Detailed Breakdown, denoted by -):
Granular breakdowns within each subgroup.

Requirements:
1. Keep the hierarchy realistic for China and the given domain.
2. Create 2 to 4 first-layer groups covering directly affected groups, institutional groups, and broader public or observer groups when relevant.
3. Keep total leaf groups between 4 and 8 for simulation efficiency.
4. Use integer population counts.
5. The hierarchy should reflect who is most relevant to the event.
6. Do not add explanations outside the hierarchy.

Example format:
## Students: 58030769
1. **Postgraduates: 3653613**
- Doctor: 556065
- Master: 3097548
2. **Undergraduates: 19656436**
- Bachelor: 19656436
""".strip()


def _parse_hierarchy_response(text: str, news_state: NewsState) -> HierarchyPlan | None:
    roots: list[ParsedHierarchyNode] = []
    current_l1: ParsedHierarchyNode | None = None
    current_l2: ParsedHierarchyNode | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            parsed = _parse_named_population(line[3:].strip())
            if not parsed:
                continue
            current_l1 = ParsedHierarchyNode(level=1, name=parsed[0], population=parsed[1])
            roots.append(current_l1)
            current_l2 = None
            continue
        second_layer = re.match(r"^\d+\.\s*\*\*(.+?)\*\*$", line)
        if second_layer and current_l1:
            parsed = _parse_named_population(second_layer.group(1).strip())
            if not parsed:
                continue
            current_l2 = ParsedHierarchyNode(level=2, name=parsed[0], population=parsed[1])
            current_l1.children.append(current_l2)
            continue
        if line.startswith("-") and current_l2:
            parsed = _parse_named_population(line[1:].strip())
            if not parsed:
                continue
            current_l2.children.append(ParsedHierarchyNode(level=3, name=parsed[0], population=parsed[1]))

    if not roots:
        return None
    return _convert_parsed_nodes_to_plan(roots, news_state)


def _parse_named_population(text: str) -> tuple[str, int] | None:
    match = re.match(r"^(.*?):\s*([\d,]+)\s*$", text)
    if not match:
        return None
    name = match.group(1).strip()
    population = int(match.group(2).replace(",", ""))
    return name, population


def _convert_parsed_nodes_to_plan(roots: list[ParsedHierarchyNode], news_state: NewsState) -> HierarchyPlan:
    tree_nodes: list[GroupProfile] = []
    leaf_groups: list[GroupProfile] = []
    level_two_groups: list[GroupProfile] = []
    event_keywords = _extract_event_keywords(news_state)

    def walk(node: ParsedHierarchyNode, parent: GroupProfile | None, path: list[str]) -> None:
        profile = GroupProfile(
            id=_build_node_id(path + [node.name]),
            name=node.name,
            description=(
                f"Representing {node.population:,} {_identity_from_group_name(node.name, news_state.category)} "
                f"reacting to the current event."
            ),
            identity=_identity_from_group_name(node.name, news_state.category),
            population=node.population,
            characteristic=_characteristic_from_name(node.name),
            layer=f"L{node.level}",
            parent_id=parent.id if parent else None,
            hierarchy_path=path + [node.name],
            focus_label=node.name.lower(),
            focus_keywords=_focus_keywords(node.name, event_keywords),
            category=_population_category_from_name(node.name),
        )
        tree_nodes.append(profile)
        if node.level == 2:
            level_two_groups.append(profile)
        if not node.children:
            leaf_groups.append(profile)
            return
        for child in node.children:
            walk(child, profile, profile.hierarchy_path)

    for root in roots:
        walk(root, None, [])
    if len(leaf_groups) > 8:
        if 4 <= len(level_two_groups) <= 8:
            leaf_groups = level_two_groups
        else:
            leaf_groups = sorted(leaf_groups, key=lambda item: item.population, reverse=True)[:8]
    return HierarchyPlan(tree_nodes=tree_nodes, leaf_groups=leaf_groups)


def _build_node_id(path: list[str]) -> str:
    slug = "_".join(path).lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")[:80]


def _identity_from_group_name(name: str, category: str) -> str:
    lowered = name.lower()
    if "student" in lowered:
        return "Chinese students"
    if "teacher" in lowered or "educator" in lowered or "professor" in lowered:
        return "Chinese educators"
    if "parent" in lowered:
        return "Chinese parents"
    if "expert" in lowered or "scholar" in lowered or "research" in lowered:
        return f"Chinese {category.lower()} experts"
    if "fan" in lowered:
        return "Chinese sports fans"
    if "public" in lowered or "citizen" in lowered:
        return "Chinese citizens"
    return f"Chinese {name}"


def _population_category_from_name(name: str) -> PopulationCategory:
    lowered = name.lower()
    if any(token in lowered for token in ["student", "fan", "parent", "victim", "public", "audience"]):
        return PopulationCategory.SUSCEPTIBLE
    if any(token in lowered for token in ["expert", "professional", "administrator", "official", "scholar"]):
        return PopulationCategory.CALM
    return PopulationCategory.AVERAGE


def _characteristic_from_name(name: str) -> str:
    category = _population_category_from_name(name)
    if category == PopulationCategory.SUSCEPTIBLE:
        return "Susceptible"
    if category == PopulationCategory.CALM:
        return "Calm"
    return "Average"


def _focus_keywords(name: str, event_keywords: list[str]) -> list[str]:
    local_keywords = [token for token in re.split(r"[^a-zA-Z]+", name.lower()) if token]
    merged = []
    for keyword in local_keywords + event_keywords:
        if keyword not in merged:
            merged.append(keyword)
    return merged[:8]


def _load_cached_hierarchy(news_state: NewsState, cache_dir: Path | None) -> HierarchyPlan | None:
    cache_path = _hierarchy_cache_path(news_state, cache_dir)
    if cache_path is None or not cache_path.exists():
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        return HierarchyPlan.model_validate(payload)
    except Exception:
        return None


def _save_hierarchy_cache(news_state: NewsState, plan: HierarchyPlan, cache_dir: Path | None) -> None:
    cache_path = _hierarchy_cache_path(news_state, cache_dir)
    if cache_path is None:
        return
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")


def _hierarchy_cache_path(news_state: NewsState, cache_dir: Path | None) -> Path | None:
    if cache_dir is None:
        return None
    event_key = news_state.event_id if news_state.event_id is not None else _build_node_id([news_state.category, news_state.title])
    return cache_dir / f"hierarchy_event_{event_key}.json"
