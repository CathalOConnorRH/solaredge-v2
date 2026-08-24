"""Async client for the SolarEdge ONE (Monitoring v2) API."""

from __future__ import annotations

from .budget import (
    BudgetPlan,
    backoff_interval,
    compute_interval,
    plan_interval,
    project_month_end_usage,
)
from .client import SolarEdgeOneClient
from .const import (
    DEFAULT_BASE_URL,
    RESOLUTION_DAY,
    RESOLUTION_HOUR,
    RESOLUTION_QUARTER_HOUR,
)
from .exceptions import (
    SolarEdgeApiError,
    SolarEdgeAuthError,
    SolarEdgeConnectionError,
    SolarEdgeError,
    SolarEdgeNotFoundError,
    SolarEdgeRateLimitError,
)
from .models import (
    ConsumptionOverview,
    Device,
    ProductionOverview,
    Site,
    SiteOverview,
    TimeSeries,
    TimeValue,
)
from .ratelimit import CreditLedger, RateLimit

__version__ = "0.2.0"

__all__ = [
    "SolarEdgeOneClient",
    "BudgetPlan",
    "backoff_interval",
    "compute_interval",
    "plan_interval",
    "project_month_end_usage",
    "DEFAULT_BASE_URL",
    "RESOLUTION_DAY",
    "RESOLUTION_HOUR",
    "RESOLUTION_QUARTER_HOUR",
    "SolarEdgeError",
    "SolarEdgeApiError",
    "SolarEdgeAuthError",
    "SolarEdgeConnectionError",
    "SolarEdgeNotFoundError",
    "SolarEdgeRateLimitError",
    "Site",
    "SiteOverview",
    "ProductionOverview",
    "ConsumptionOverview",
    "Device",
    "TimeSeries",
    "TimeValue",
    "CreditLedger",
    "RateLimit",
]
