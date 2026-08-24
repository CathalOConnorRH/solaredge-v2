"""Async client for the SolarEdge ONE (Monitoring v2) API."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import aiohttp

from .const import (
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    HEADER_ACCOUNT_KEY,
    HEADER_API_KEY,
)
from .exceptions import (
    SolarEdgeApiError,
    SolarEdgeAuthError,
    SolarEdgeConnectionError,
    SolarEdgeNotFoundError,
    SolarEdgeRateLimitError,
)
from .models import (
    Device,
    Site,
    SiteOverview,
    TimeSeries,
    parse_device_list,
    parse_site_list,
)
from .ratelimit import CreditLedger, RateLimit


def _fmt_time(value: str | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class SolarEdgeOneClient:
    """Thin async wrapper over the SolarEdge ONE v2 REST API.

    The caller injects an ``aiohttp.ClientSession``. Only endpoints confirmed in
    Phase 0 are implemented; query-param names for the time-series endpoints are
    best-effort and may need adjustment once the docs are captured.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        *,
        account_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        ledger: CreditLedger | None = None,
    ) -> None:
        self._session = session
        self._api_key = api_key
        self._account_key = account_key
        self._base_url = base_url.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self.ledger = ledger
        self.rate_limit: RateLimit | None = None

    # -- internals -----------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", HEADER_API_KEY: self._api_key}
        if self._account_key:
            headers[HEADER_ACCOUNT_KEY] = self._account_key
        return headers

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self._base_url}{path}"
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        try:
            async with self._session.get(
                url,
                headers=self._headers(),
                params=clean_params or None,
                timeout=self._timeout,
            ) as resp:
                self.rate_limit = RateLimit.from_headers(resp.headers)
                await self._raise_for_status(resp)
                data = await resp.json()
        except aiohttp.ClientError as err:
            raise SolarEdgeConnectionError(f"Request to {path} failed: {err}") from err

        # Count the credit only on a successful call (1 call = 1 credit).
        if self.ledger is not None:
            self.ledger.record(now=datetime.now(UTC))
        return data

    async def _raise_for_status(self, resp: aiohttp.ClientResponse) -> None:
        if resp.status < 400:
            return
        payload: Any = None
        try:
            payload = await resp.json()
        except (aiohttp.ContentTypeError, ValueError):
            payload = await resp.text()

        if resp.status in (401, 403):
            raise SolarEdgeAuthError(
                "Authentication failed — check the API key",
                status=resp.status,
                payload=payload,
            )
        if resp.status == 404:
            raise SolarEdgeNotFoundError(
                f"Resource not found: {resp.url.path}",
                status=resp.status,
                payload=payload,
            )
        if resp.status == 429:
            retry_after = _parse_retry_after(resp.headers.get("Retry-After"))
            raise SolarEdgeRateLimitError(
                "Rate limit exceeded",
                retry_after=retry_after,
                status=resp.status,
                payload=payload,
            )
        raise SolarEdgeApiError(
            f"Unexpected API error (HTTP {resp.status})",
            status=resp.status,
            payload=payload,
        )

    # -- endpoints -----------------------------------------------------------
    async def get_sites(self) -> list[Site]:
        """``GET /sites`` — all sites visible to the token."""
        return parse_site_list(await self._get("/sites"))

    async def get_site_overview(self, site_id: int | str) -> SiteOverview:
        """``GET /sites/{id}/overview`` — cumulative production/consumption."""
        return SiteOverview.from_dict(await self._get(f"/sites/{site_id}/overview"))

    async def get_devices(self, site_id: int | str) -> list[Device]:
        """``GET /sites/{id}/devices`` — site inventory."""
        return parse_device_list(await self._get(f"/sites/{site_id}/devices"))

    async def get_energy(
        self,
        site_id: int | str,
        *,
        date_from: str | datetime | None = None,
        date_to: str | datetime | None = None,
        resolution: str | None = None,
    ) -> TimeSeries:
        """``GET /sites/{id}/energy`` — energy time series (Wh per interval)."""
        params = {
            "from": _fmt_time(date_from),
            "to": _fmt_time(date_to),
            "resolution": resolution,
        }
        return TimeSeries.from_dict(await self._get(f"/sites/{site_id}/energy", params))

    async def get_power(
        self,
        site_id: int | str,
        *,
        date_from: str | datetime | None = None,
        date_to: str | datetime | None = None,
        resolution: str | None = None,
    ) -> TimeSeries:
        """``GET /sites/{id}/power`` — power time series (W, 15-min average)."""
        params = {
            "from": _fmt_time(date_from),
            "to": _fmt_time(date_to),
            "resolution": resolution,
        }
        return TimeSeries.from_dict(await self._get(f"/sites/{site_id}/power", params))

    async def get_alerts(self, site_id: int | str) -> list[dict[str, Any]]:
        """``GET /sites/{id}/alerts`` — returns a list (empty when none)."""
        data = await self._get(f"/sites/{site_id}/alerts")
        if isinstance(data, dict):
            for key in ("alerts", "alert", "data", "items"):
                value = data.get(key)
                if isinstance(value, list):
                    return cast("list[dict[str, Any]]", value)
            return []
        if isinstance(data, list):
            return cast("list[dict[str, Any]]", data)
        return []

    async def validate(self) -> list[Site]:
        """Cheapest credential check for a config flow: list sites.

        Raises ``SolarEdgeAuthError`` on bad credentials.
        """
        return await self.get_sites()


def _parse_retry_after(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None
