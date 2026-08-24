# CLAUDE.md — solaredge-v2 / `aiosolaredge-one` (API client library)

Onboarding for an AI agent (or human) picking up this repo cold.

## What this repo is

The **`aiosolaredge-one`** PyPI package: a standalone **async Python client** for
SolarEdge's v2 **"SolarEdge ONE"** monitoring API, plus the credit-budget pacing
math the Home Assistant integration uses to schedule polling.

- Published to PyPI: <https://pypi.org/project/aiosolaredge-one/> (0.2.0 live).
- Repo `git@github.com:CathalOConnorRH/solaredge-v2.git` (PRIVATE), default
  branch `main`. `src/` layout, built with hatchling. Ships `py.typed`.

## Two-repo relationship

This library is consumed by the **integration** repo `ha-solaredge-one`
(`../ha-solaredge-one`, PUBLIC). That repo pins `aiosolaredge-one==X.Y.Z` in its
`manifest.json` and installs it from PyPI. **Any breaking API change here needs a
new release + a matching pin bump there.** See `../ha-solaredge-one/CLAUDE.md`.

## Dev environment

One shared test venv serves **both** repos and lives **here**:

```
/Users/catoconn/Workspace/Personal/solaredge-v2/.venv-test   # Python 3.13
```

It has this library installed **editable** (`pip install -e .`) alongside
`homeassistant` + `pytest-homeassistant-custom-component` (the integration tests
share it). After changing library source, editable install means no reinstall is
needed for tests here; but if you bump the version, re-run `pip install -e .` so
dist metadata matches the integration's manifest pin.

```bash
VENV=/Users/catoconn/Workspace/Personal/solaredge-v2/.venv-test/bin

$VENV/python -m pytest              # library tests (from this repo root)
$VENV/ruff check src tests
$VENV/mypy src                      # mypy is configured strict
```

`pyproject.toml`: ruff `line-length = 100`, `[tool.mypy] strict = true`,
`requires-python = ">=3.11"` (runtime), only runtime dep is `aiohttp>=3.9`. CI
(`.github/workflows/ci.yml`) runs ruff + mypy + pytest for the library.

## Code map (`src/aiosolaredge_one/`)

- `client.py` — `SolarEdgeOneClient`: async methods `get_sites`,
  `get_site_overview`, `get_devices`, `get_energy`, `get_power`, `get_alerts`,
  `validate`. Header auth (`X-API-Key`, optional `X-Account-Key`). `get_energy`
  takes `date_from` / `date_to` / `resolution` (sent as `from`/`to`/`resolution`).
- `models.py` — typed dataclasses: `Site`, `SiteOverview` (+ `ProductionOverview`,
  `ConsumptionOverview`), `Device`, `TimeSeries`/`TimeValue`. `TimeSeries` has
  `.total` (sum of non-null), `.latest_value`, `.non_null_values`, `.values`.
- `budget.py` — pure pacing math: `BudgetPlan`, `compute_interval`,
  `plan_interval`, `project_month_end_usage`, `backoff_interval`, `cpm_floor`.
  Remaining-budget-aware and self-correcting. No I/O — easy to unit-test.
- `ratelimit.py` — `CreditLedger` (monthly spend accounting) + `RateLimit`.
- `exceptions.py` — `SolarEdgeError` + `SolarEdgeAuthError`,
  `SolarEdgeRateLimitError` (has `retry_after`), `SolarEdgeNotFoundError`.
- `const.py` — base URL, defaults. `__init__.py` re-exports the public API and
  defines `__version__`.

## Confirmed API facts (from live capture)

- Base URL `https://monitoringapi.solaredge.com/v2`. `X-API-Key` alone works for
  Site Owner; `X-Account-Key` is for Fleet. Hierarchy Fleet → Site → Device.
- Working endpoints (1 credit each): `/sites`, `/sites/{id}/overview`,
  `/sites/{id}/devices`, `/sites/{id}/energy`, `/sites/{id}/power`,
  `/sites/{id}/alerts`.
- `/overview` returns **TODAY's** running Wh totals, **not lifetime** (resets at
  midnight). No lifetime field exists there.
- `/energy` accepts resolutions **DAY / WEEK / MONTH / YEAR** (HOUR → 400); the
  sum is identical across resolutions. A YEAR call from install date returns one
  bucket per year → **sum = lifetime**, current-year bucket = year-to-date.
- `/power` is a QUARTER_HOUR time series; current power = last non-null point.
- Rate limit: per-minute only in headers (`x-ratelimit-*-minute`); the monthly
  ~2000-credit quota is **not** in headers → track locally (`CreditLedger`).
- `/sites` shape: `{"sites":{"count":N,"site":[{siteId,...}]}}` (singular `site`).
- 404 (paths not yet available): `/storage`, `/battery`, `/powerFlow`,
  `/environmentalBenefits`, `/summary`.

## Testing conventions

- Tests use a **hand-rolled `FakeSession`** in `tests/conftest.py`, NOT
  `aioresponses` (incompatible with aiohttp 3.14). It implements only the surface
  the client uses: `session.get(...)` → async-CM response with `.status`,
  `.headers`, `.url`, `.json()`, `.text()`. Fixtures are JSON in `tests/fixtures/`.
- Keep `mypy --strict` and ruff clean; both are enforced in CI.

## Release process (Trusted Publishing / OIDC — already configured)

Pending publishers are registered on TestPyPI + PyPI (project `aiosolaredge-one`,
owner `CathalOConnorRH`, repo `solaredge-v2`, workflow `publish.yml`, envs
`testpypi`/`pypi`). No re-setup needed. To cut a release:

1. Bump `version` in `pyproject.toml` **and** `__version__` in
   `src/aiosolaredge_one/__init__.py`, update `CHANGELOG.md`.
2. Commit, `git tag vX.Y.Z`, push.
3. Optional dry run: `gh workflow run publish.yml` (workflow_dispatch → TestPyPI),
   verify a clean install.
4. `gh release create vX.Y.Z` — the release event triggers the PyPI job.
5. Bump the pin in `../ha-solaredge-one/custom_components/solaredge_one/
   manifest.json` (+ its CI) to the new version.

Full details in `RELEASING.md`.

## Security

Never commit or store the SolarEdge API key. Do not print it. (Owner advised to
rotate the key that was exposed in chat.)
