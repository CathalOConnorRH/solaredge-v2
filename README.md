# aiosolaredge-one

Async Python client for the **SolarEdge ONE** (Monitoring API v2) platform. It
powers the
[SolarEdge ONE Home Assistant integration](https://github.com/CathalOConnorRH/ha-solaredge-one),
which lives in its own repo and depends on this package.

Base URL: `https://monitoringapi.solaredge.com/v2` · Auth: `X-API-Key` header
(plus optional `X-Account-Key` for Fleet accounts).

> Status: **alpha**. Endpoint coverage and models are derived from Phase 0 live
> captures. Some query-param names and the storage/battery/environmental paths
> are still unconfirmed pending docs.

## Install (dev)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Usage

```python
import aiohttp
from aiosolaredge_one import SolarEdgeOneClient

async with aiohttp.ClientSession() as session:
    client = SolarEdgeOneClient(session, api_key="...")
    sites = await client.get_sites()
    overview = await client.get_site_overview(sites[0].site_id)
    print(overview.production.total, overview.production.unit)
    power = await client.get_power(sites[0].site_id)
    print("current power:", power.latest_value, power.unit)
```

## What it covers (Phase 0-confirmed endpoints)

| Method | Endpoint |
|--------|----------|
| `get_sites()` | `GET /sites` |
| `get_site_overview(id)` | `GET /sites/{id}/overview` |
| `get_devices(id)` | `GET /sites/{id}/devices` |
| `get_energy(id, ...)` | `GET /sites/{id}/energy` |
| `get_power(id, ...)` | `GET /sites/{id}/power` |
| `get_alerts(id)` | `GET /sites/{id}/alerts` |

Rate limiting: the client exposes `client.rate_limit` (per-minute limit +
remaining, parsed from response headers) and an optional `CreditLedger` for
tracking the monthly quota locally (not exposed by the API).
