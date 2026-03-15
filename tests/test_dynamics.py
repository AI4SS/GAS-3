from app.schema.agent_state import GroupProfile, GroupState, PopulationCategory
from app.schema.simulation import RoundContext
from app.services.dynamics import build_attitude_state, estimate_metrics, sync_internal_groups


def test_polarized_group_creates_internal_groups():
    profile = GroupProfile(
        id="g1",
        name="Test",
        description="Test group",
        identity="testers",
        population=1000,
        characteristic="susceptible",
        category=PopulationCategory.SUSCEPTIBLE,
    )
    state = GroupState()
    state.attitude = build_attitude_state(2.0, 2.0, profile)
    sync_internal_groups(state, profile.population)
    assert state.internal_groups["optimism"].population + state.internal_groups["pessimism"].population == 1000


def test_estimate_metrics_monotonic_constraints():
    profile = GroupProfile(
        id="g2",
        name="Test",
        description="Test group",
        identity="testers",
        population=10_000,
        characteristic="calm",
        category=PopulationCategory.CALM,
    )
    state = GroupState()
    state.attitude.optimism = 0.4
    metrics = estimate_metrics(profile, state, RoundContext(current_round=3, total_rounds=7))
    assert metrics["views"] >= metrics["likes"] >= metrics["comments"]
