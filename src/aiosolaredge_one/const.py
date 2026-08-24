"""Constants for the SolarEdge ONE (Monitoring v2) API client."""

from __future__ import annotations

DEFAULT_BASE_URL = "https://monitoringapi.solaredge.com/v2"
DEFAULT_TIMEOUT = 30.0

# Auth headers (v2 uses headers, not a bearer token).
HEADER_API_KEY = "X-API-Key"
HEADER_ACCOUNT_KEY = "X-Account-Key"

# Rate-limit response headers observed in Phase 0. Only per-minute is exposed;
# the monthly credit quota must be tracked locally (see CreditLedger).
HEADER_RATELIMIT_LIMIT = "x-ratelimit-limit-minute"
HEADER_RATELIMIT_REMAINING = "x-ratelimit-remaining-minute"

# Resolutions accepted by the time-series endpoints (values seen: QUARTER_HOUR).
RESOLUTION_QUARTER_HOUR = "QUARTER_HOUR"
RESOLUTION_HOUR = "HOUR"
RESOLUTION_DAY = "DAY"
