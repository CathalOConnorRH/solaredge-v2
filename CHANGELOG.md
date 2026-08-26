# Changelog

All notable changes to `aiosolaredge-one` are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-08-26

### Added
- Client methods for more v2 endpoints: `get_site_details` (`GET /sites/{id}`),
  `get_fleet_alerts` (`GET /alerts`), `get_environmental_benefits`
  (`GET /sites/{id}/environmental-benefits`), `get_storage_telemetry`
  (`GET /sites/{id}/storage/telemetry`, site-wide or per-serial), and
  `get_lifetime_energy` (energy with `resolution=TOTAL`).
- `EnvironmentalBenefits` model (`co2Emissions`, `evMiles`) and `parse_site`.
- Resolution constants `RESOLUTION_WEEK/MONTH/YEAR/TOTAL` and the `RESOLUTIONS`
  tuple. `get_energy` accepts the full v2 resolution set (min `QUARTER_HOUR`);
  `TOTAL` collapses the range to one bucket for lifetime/range totals.

### Notes
- `get_storage_telemetry` returns the raw payload — the per-metric telemetry
  shape has not been captured from a live battery site, so no typed model is
  imposed yet.

## [0.2.0] - 2026-08-24

### Added
- `budget` module: credit-budget pacing math (`compute_interval`,
  `plan_interval`, `BudgetPlan`, `project_month_end_usage`, `backoff_interval`,
  `cpm_floor`) for remaining-budget-aware, self-correcting poll scheduling.

## [0.1.0] - 2026-08-24

### Added
- Initial async client for the SolarEdge ONE (Monitoring v2) API:
  `get_sites`, `get_site_overview`, `get_devices`, `get_energy`, `get_power`,
  `get_alerts`, `validate`.
- Typed models (`Site`, `SiteOverview`, `Device`, `TimeSeries`, …), typed
  exceptions, `CreditLedger` local monthly accounting, and `RateLimit` header
  parsing.
