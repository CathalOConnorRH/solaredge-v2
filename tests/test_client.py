"""Client tests against the Phase 0 captured fixtures (no live API)."""

from __future__ import annotations

import pytest
from conftest import FakeSession, load_fixture

from aiosolaredge_one import (
    CreditLedger,
    SolarEdgeAuthError,
    SolarEdgeNotFoundError,
    SolarEdgeOneClient,
    SolarEdgeRateLimitError,
)

SITE_ID = 3066774

RATE_HEADERS = {
    "x-ratelimit-limit-minute": "10",
    "x-ratelimit-remaining-minute": "9",
}


def make_client(session: FakeSession, **kwargs: object) -> SolarEdgeOneClient:
    return SolarEdgeOneClient(session, api_key="test-key", **kwargs)  # type: ignore[arg-type]


async def test_get_sites(session: FakeSession) -> None:
    session.add("/sites", payload=load_fixture("sites"), headers=RATE_HEADERS)
    sites = await make_client(session).get_sites()

    assert len(sites) == 1
    site = sites[0]
    assert site.site_id == SITE_ID
    assert site.peak_power == 5.68
    assert site.is_active is True


async def test_get_site_overview(session: FakeSession) -> None:
    session.add(f"/sites/{SITE_ID}/overview", payload=load_fixture("overview"))
    overview = await make_client(session).get_site_overview(SITE_ID)

    assert overview.site_id == SITE_ID
    assert overview.production.total == 26290.0
    assert overview.production.unit == "WH"
    # No consumption meter on this site -> nulls parsed as None.
    assert overview.consumption.total is None
    assert overview.production.to_grid is None


async def test_get_devices(session: FakeSession) -> None:
    session.add(f"/sites/{SITE_ID}/devices", payload=load_fixture("devices"))
    devices = await make_client(session).get_devices(SITE_ID)

    assert len(devices) == 1
    inverter = devices[0]
    assert inverter.type == "INVERTER"
    assert inverter.connected_optimizers == 14
    assert inverter.active is True
    assert inverter.part_number == "SE5000H-RW000BNN4"


async def test_get_energy(session: FakeSession) -> None:
    session.add(f"/sites/{SITE_ID}/energy", payload=load_fixture("energy"))
    energy = await make_client(session).get_energy(SITE_ID)

    assert energy.unit == "WH"
    assert energy.resolution == "QUARTER_HOUR"
    assert len(energy.values) > 0
    assert energy.total > 0
    assert energy.latest_value is not None


async def test_get_power_latest(session: FakeSession) -> None:
    session.add(f"/sites/{SITE_ID}/power", payload=load_fixture("power"))
    power = await make_client(session).get_power(SITE_ID)

    assert power.unit == "W"
    # The last entry in the fixture is null (incomplete interval); latest_value
    # must skip it and return the last real reading (~982.2 W).
    assert power.values[-1].value is None
    assert power.latest_value == pytest.approx(982.2318, rel=1e-4)


async def test_get_alerts_empty(session: FakeSession) -> None:
    session.add(f"/sites/{SITE_ID}/alerts", payload=load_fixture("alerts"))
    alerts = await make_client(session).get_alerts(SITE_ID)

    assert alerts == []


async def test_rate_limit_parsed(session: FakeSession) -> None:
    session.add("/sites", payload=load_fixture("sites"), headers=RATE_HEADERS)
    client = make_client(session)
    await client.get_sites()

    assert client.rate_limit is not None
    assert client.rate_limit.limit_minute == 10
    assert client.rate_limit.remaining_minute == 9


async def test_credit_ledger_increments(session: FakeSession) -> None:
    ledger = CreditLedger(monthly_budget=2000)
    session.add("/sites", payload=load_fixture("sites"))
    session.add(f"/sites/{SITE_ID}/overview", payload=load_fixture("overview"))
    client = make_client(session, ledger=ledger)
    await client.get_sites()
    await client.get_site_overview(SITE_ID)

    assert ledger.used == 2
    assert ledger.remaining() == 1998


async def test_auth_error(session: FakeSession) -> None:
    session.add("/sites", status=403, payload={"message": "forbidden"})
    with pytest.raises(SolarEdgeAuthError):
        await make_client(session).get_sites()


async def test_not_found_error(session: FakeSession) -> None:
    session.add(f"/sites/{SITE_ID}/overview", status=404, payload={"message": "nope"})
    with pytest.raises(SolarEdgeNotFoundError):
        await make_client(session).get_site_overview(SITE_ID)


async def test_rate_limit_error_with_retry_after(session: FakeSession) -> None:
    session.add("/sites", status=429, headers={"Retry-After": "42"},
                payload={"message": "slow down"})
    with pytest.raises(SolarEdgeRateLimitError) as excinfo:
        await make_client(session).get_sites()

    assert excinfo.value.retry_after == 42.0


async def test_ledger_not_incremented_on_error(session: FakeSession) -> None:
    ledger = CreditLedger(monthly_budget=2000)
    session.add("/sites", status=403, payload={})
    with pytest.raises(SolarEdgeAuthError):
        await make_client(session, ledger=ledger).get_sites()

    assert ledger.used == 0
