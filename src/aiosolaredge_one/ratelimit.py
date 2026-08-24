"""Rate-limit + credit tracking helpers.

Phase 0 finding: the API exposes only a *per-minute* limit via response headers
(``x-ratelimit-limit-minute`` / ``x-ratelimit-remaining-minute``). The monthly
credit quota (e.g. 2000/month) is NOT exposed, so it must be tracked locally.
``CreditLedger`` provides that local accounting and is JSON-serialisable so the
Home Assistant integration can persist it across restarts.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .const import HEADER_RATELIMIT_LIMIT, HEADER_RATELIMIT_REMAINING


def _month_key(now: datetime) -> str:
    return f"{now.year:04d}-{now.month:02d}"


@dataclass(slots=True)
class RateLimit:
    """Per-minute rate-limit snapshot parsed from response headers."""

    limit_minute: int | None = None
    remaining_minute: int | None = None

    @classmethod
    def from_headers(cls, headers: Mapping[str, str]) -> RateLimit:
        # Header names are case-insensitive; aiohttp's CIMultiDict handles that,
        # but fall back to a manual lower-cased lookup for plain dicts.
        def _get(name: str) -> str | None:
            if name in headers:
                return headers[name]
            lowered = {k.lower(): v for k, v in headers.items()}
            return lowered.get(name.lower())

        def _int(value: str | None) -> int | None:
            if value is None:
                return None
            try:
                return int(value)
            except ValueError:
                return None

        return cls(
            limit_minute=_int(_get(HEADER_RATELIMIT_LIMIT)),
            remaining_minute=_int(_get(HEADER_RATELIMIT_REMAINING)),
        )


@dataclass(slots=True)
class CreditLedger:
    """Local monthly-credit accounting (the API does not expose monthly quota).

    Assumes 1 API call = 1 credit (Phase 0 finding). Resets automatically when
    the calendar month changes.
    """

    monthly_budget: int
    used: int = 0
    month: str | None = None

    def record(self, cost: int = 1, *, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        key = _month_key(now)
        if self.month != key:
            self.month = key
            self.used = 0
        self.used += cost

    def remaining(self, *, now: datetime | None = None) -> int:
        now = now or datetime.now(UTC)
        if self.month != _month_key(now):
            return self.monthly_budget
        return max(0, self.monthly_budget - self.used)

    def would_exceed(self, cost: int = 1, *, now: datetime | None = None) -> bool:
        return self.remaining(now=now) < cost

    def to_dict(self) -> dict[str, Any]:
        return {"monthly_budget": self.monthly_budget, "used": self.used, "month": self.month}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CreditLedger:
        return cls(
            monthly_budget=int(data.get("monthly_budget", 0)),
            used=int(data.get("used", 0)),
            month=data.get("month"),
        )
