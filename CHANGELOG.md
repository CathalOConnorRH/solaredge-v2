# Changelog

All notable changes to `aiosolaredge-one` are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
