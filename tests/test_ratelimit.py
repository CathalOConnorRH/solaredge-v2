"""Tests for rate-limit parsing and the local credit ledger."""

from __future__ import annotations

from datetime import UTC, datetime

from aiosolaredge_one import CreditLedger, RateLimit


def test_ratelimit_from_headers_case_insensitive() -> None:
    rl = RateLimit.from_headers(
        {"X-RateLimit-Limit-Minute": "10", "X-RateLimit-Remaining-Minute": "3"}
    )
    assert rl.limit_minute == 10
    assert rl.remaining_minute == 3


def test_ratelimit_from_headers_missing() -> None:
    rl = RateLimit.from_headers({})
    assert rl.limit_minute is None
    assert rl.remaining_minute is None


def test_ledger_record_and_remaining() -> None:
    now = datetime(2026, 8, 24, tzinfo=UTC)
    ledger = CreditLedger(monthly_budget=2000)
    for _ in range(5):
        ledger.record(now=now)
    assert ledger.used == 5
    assert ledger.remaining(now=now) == 1995


def test_ledger_resets_on_month_change() -> None:
    aug = datetime(2026, 8, 31, tzinfo=UTC)
    sep = datetime(2026, 9, 1, tzinfo=UTC)
    ledger = CreditLedger(monthly_budget=2000)
    ledger.record(now=aug)
    ledger.record(now=aug)
    assert ledger.used == 2
    # First call in the new month resets the counter.
    ledger.record(now=sep)
    assert ledger.used == 1
    assert ledger.month == "2026-09"
    assert ledger.remaining(now=sep) == 1999


def test_ledger_would_exceed() -> None:
    now = datetime(2026, 8, 24, tzinfo=UTC)
    ledger = CreditLedger(monthly_budget=3)
    ledger.record(now=now)
    ledger.record(now=now)
    ledger.record(now=now)
    assert ledger.remaining(now=now) == 0
    assert ledger.would_exceed(now=now) is True


def test_ledger_roundtrip() -> None:
    ledger = CreditLedger(monthly_budget=2000, used=17, month="2026-08")
    restored = CreditLedger.from_dict(ledger.to_dict())
    assert restored == ledger
