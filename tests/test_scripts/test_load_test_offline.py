import pytest

from scripts.load_test_offline import build_plan, percentile


def test_percentile_interpolates_sorted_values() -> None:
    assert percentile([4, 1, 3, 2], 0.50) == 2.5
    assert percentile([4, 1, 3, 2], 0.95) == pytest.approx(3.85)


def test_build_plan_rotates_all_scenarios_deterministically() -> None:
    assert build_plan("all", 8) == [
        "happy-path",
        "change-pickup",
        "change-destination",
        "change-vehicle",
        "out-of-scope",
        "operator-handoff",
        "happy-path",
        "change-pickup",
    ]


def test_build_plan_repeats_one_selected_scenario() -> None:
    assert build_plan("happy-path", 3) == ["happy-path", "happy-path", "happy-path"]
