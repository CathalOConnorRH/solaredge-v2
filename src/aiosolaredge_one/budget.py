"""Credit-budget pacing math (HA-agnostic, pure functions).

The SolarEdge ONE API exposes only a per-minute rate limit; the monthly credit
quota (e.g. 2000/month) is tracked locally via :class:`CreditLedger`. This module
turns "credits remaining this month" into "how long to wait before the next poll"
so a caller spends its budget evenly instead of burning it early.

The core function, :func:`compute_interval`, is *remaining-budget aware*: it
paces against the credits still available for the rest of the month, so it
self-corrects. If earlier cycles overspent, later intervals lengthen; if the
budget is nearly exhausted it backs off to ``max_interval``. This doubles as the
budget guard — no separate "are we over budget?" branch is needed for pacing.

All functions are pure (no clock, no I/O) so they can be unit-tested by feeding
in ``remaining_credits`` / ``seconds_until_reset`` directly.
"""

from __future__ import annotations

from dataclasses import dataclass

# Sensible defaults; the HA integration overrides these from config/options.
DEFAULT_SAFETY_FACTOR = 0.7
DEFAULT_NIGHT_FACTOR = 3.0
DEFAULT_MIN_INTERVAL = 60.0  # seconds — never poll faster than once a minute
DEFAULT_MAX_INTERVAL = 6 * 60 * 60.0  # seconds — poll at least every 6h


def _clamp(value: float, low: float, high: float) -> float:
    if low > high:
        # A pathological config (floor above ceiling); prefer respecting the
        # per-minute floor over the ceiling to avoid violating the hard limit.
        return low
    return max(low, min(high, value))


def cpm_floor(credits_per_cycle: int, calls_per_minute: int) -> float:
    """Minimum seconds between cycles so we never exceed the per-minute limit.

    A cycle issues ``credits_per_cycle`` calls; spacing cycles at least this far
    apart keeps the average call rate at or below ``calls_per_minute``.
    """
    cpm = max(1, calls_per_minute)
    return 60.0 * max(1, credits_per_cycle) / cpm


@dataclass(slots=True, frozen=True)
class BudgetPlan:
    """User-configurable pacing parameters for one config entry."""

    monthly_budget: int
    calls_per_minute: int = 10
    credits_per_cycle: int = 2
    safety_factor: float = DEFAULT_SAFETY_FACTOR
    night_factor: float = DEFAULT_NIGHT_FACTOR
    min_interval: float = DEFAULT_MIN_INTERVAL
    max_interval: float = DEFAULT_MAX_INTERVAL

    @property
    def target_credits(self) -> float:
        """Credits we actually aim to spend per month (budget × safety)."""
        return self.monthly_budget * self.safety_factor


def compute_interval(
    *,
    remaining_credits: float,
    seconds_until_reset: float,
    credits_per_cycle: int,
    calls_per_minute: int,
    min_interval: float = DEFAULT_MIN_INTERVAL,
    max_interval: float = DEFAULT_MAX_INTERVAL,
    is_night: bool = False,
    night_factor: float = DEFAULT_NIGHT_FACTOR,
) -> float:
    """Seconds to wait before the next poll, paced to the remaining budget.

    ``remaining_credits`` should already have the safety factor applied (i.e. it
    is the *target* remaining, not the raw quota). When it drops below one
    cycle's cost — or the month has effectively ended — this returns
    ``max_interval`` so polling backs off instead of overspending.
    """
    floor = max(min_interval, cpm_floor(credits_per_cycle, calls_per_minute))
    if remaining_credits < credits_per_cycle or seconds_until_reset <= 0:
        return max(max_interval, floor)

    cycles_left = remaining_credits / max(1, credits_per_cycle)
    interval = seconds_until_reset / cycles_left
    if is_night:
        interval *= night_factor
    return _clamp(interval, floor, max_interval)


def plan_interval(
    plan: BudgetPlan,
    *,
    used_this_month: int,
    seconds_until_reset: float,
    is_night: bool = False,
) -> float:
    """Convenience wrapper: interval for a :class:`BudgetPlan` given usage."""
    remaining = max(0.0, plan.target_credits - used_this_month)
    return compute_interval(
        remaining_credits=remaining,
        seconds_until_reset=seconds_until_reset,
        credits_per_cycle=plan.credits_per_cycle,
        calls_per_minute=plan.calls_per_minute,
        min_interval=plan.min_interval,
        max_interval=plan.max_interval,
        is_night=is_night,
        night_factor=plan.night_factor,
    )


def project_month_end_usage(
    *, used_this_month: int, elapsed_seconds: float, total_seconds: float
) -> float:
    """Linear projection of end-of-month spend from usage so far.

    Used to decide whether to raise a "you'll blow the budget" repair issue.
    Returns the current usage unchanged until a little time has elapsed (avoids
    wild extrapolation from the first few seconds of the month).
    """
    if elapsed_seconds <= 0 or total_seconds <= 0:
        return float(used_this_month)
    return used_this_month * total_seconds / elapsed_seconds


def backoff_interval(
    attempt: int,
    *,
    base: float = 60.0,
    cap: float = 60 * 60.0,
    retry_after: float | None = None,
) -> float:
    """Exponential backoff after a 429, honouring ``Retry-After`` when present.

    ``attempt`` is 1-based (first failure → ``base``). The result is capped at
    ``cap`` and never shorter than a supplied ``Retry-After``.
    """
    exp = base * (2.0 ** max(0, attempt - 1))
    interval = min(exp, cap)
    if retry_after is not None:
        interval = max(interval, retry_after)
    return interval
