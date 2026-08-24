"""Tests for the credit-budget pacing math."""

from __future__ import annotations

import pytest

from aiosolaredge_one import (
    BudgetPlan,
    backoff_interval,
    compute_interval,
    plan_interval,
    project_month_end_usage,
)
from aiosolaredge_one.budget import cpm_floor

MONTH_SECONDS = 30 * 24 * 3600.0


def test_cpm_floor_respects_per_minute_limit() -> None:
    # 2 calls/cycle at 10 calls/min → at least 12s between cycles.
    assert cpm_floor(2, 10) == pytest.approx(12.0)
    # Never divides by zero for a nonsense limit.
    assert cpm_floor(1, 0) == pytest.approx(60.0)


def test_interval_paces_budget_evenly() -> None:
    # Fresh month, full target: spread cycles across the whole month.
    interval = compute_interval(
        remaining_credits=1400,  # 2000 * 0.7
        seconds_until_reset=MONTH_SECONDS,
        credits_per_cycle=2,
        calls_per_minute=10,
    )
    cycles = 1400 / 2
    assert interval == pytest.approx(MONTH_SECONDS / cycles)  # ~123s


def test_interval_backs_off_when_budget_exhausted() -> None:
    interval = compute_interval(
        remaining_credits=1,  # less than one cycle's cost
        seconds_until_reset=MONTH_SECONDS,
        credits_per_cycle=2,
        calls_per_minute=10,
        max_interval=6 * 3600,
    )
    assert interval == 6 * 3600


def test_interval_never_faster_than_per_minute_floor() -> None:
    # Tons of budget, almost no time left → would want to poll constantly, but
    # the per-minute floor caps it.
    interval = compute_interval(
        remaining_credits=100000,
        seconds_until_reset=10,
        credits_per_cycle=2,
        calls_per_minute=10,
        min_interval=1,
    )
    assert interval == pytest.approx(cpm_floor(2, 10))  # 12s


def test_night_factor_lengthens_interval() -> None:
    kwargs = dict(
        remaining_credits=1400,
        seconds_until_reset=MONTH_SECONDS,
        credits_per_cycle=2,
        calls_per_minute=10,
        max_interval=24 * 3600,
    )
    day = compute_interval(is_night=False, **kwargs)
    night = compute_interval(is_night=True, night_factor=3.0, **kwargs)
    assert night == pytest.approx(day * 3.0)


def test_plan_interval_applies_safety_factor() -> None:
    plan = BudgetPlan(monthly_budget=2000, calls_per_minute=10, credits_per_cycle=2)
    assert plan.target_credits == pytest.approx(1400.0)
    interval = plan_interval(
        plan, used_this_month=0, seconds_until_reset=MONTH_SECONDS
    )
    assert interval == pytest.approx(MONTH_SECONDS / (1400 / 2))


def test_projection_extrapolates_linearly() -> None:
    # Spent 100 in the first day of a 30-day month → ~3000 projected.
    projected = project_month_end_usage(
        used_this_month=100, elapsed_seconds=24 * 3600, total_seconds=MONTH_SECONDS
    )
    assert projected == pytest.approx(3000.0)


def test_projection_is_stable_at_month_start() -> None:
    assert project_month_end_usage(
        used_this_month=5, elapsed_seconds=0, total_seconds=MONTH_SECONDS
    ) == pytest.approx(5.0)


def test_backoff_is_exponential_and_capped() -> None:
    assert backoff_interval(1, base=60, cap=3600) == 60
    assert backoff_interval(2, base=60, cap=3600) == 120
    assert backoff_interval(3, base=60, cap=3600) == 240
    assert backoff_interval(10, base=60, cap=3600) == 3600  # capped
    # Retry-After wins when longer than the exponential value.
    assert backoff_interval(1, base=60, cap=3600, retry_after=200) == 200


def test_simulated_month_stays_under_budget() -> None:
    """A full simulated month of adaptive polling never exceeds the budget.

    Steps the clock forward one interval at a time, recording credits each
    cycle and recomputing the interval from what's left. This is the Phase 3
    DoD "simulated run stays under budget" check.
    """
    plan = BudgetPlan(monthly_budget=2000, calls_per_minute=10, credits_per_cycle=2)
    elapsed = 0.0
    used = 0
    cycles = 0
    while elapsed < MONTH_SECONDS and cycles < 100_000:
        interval = plan_interval(
            plan,
            used_this_month=used,
            seconds_until_reset=MONTH_SECONDS - elapsed,
            # Alternate day/night roughly every 12h to exercise night slowdown.
            is_night=(int(elapsed // (12 * 3600)) % 2 == 1),
        )
        elapsed += interval
        if elapsed >= MONTH_SECONDS:
            break
        used += plan.credits_per_cycle
        cycles += 1

    assert used <= plan.monthly_budget  # hard quota never breached
    # Night slowdown means we spend somewhat under the safety target, which is
    # fine — the guarantee is "under budget", not "exactly at target".
    assert used <= plan.target_credits + plan.credits_per_cycle
    assert cycles > 100  # actually polled a meaningful number of times
