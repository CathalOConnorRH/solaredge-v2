"""Exceptions raised by the SolarEdge ONE client."""

from __future__ import annotations


class SolarEdgeError(Exception):
    """Base class for all SolarEdge ONE client errors."""


class SolarEdgeConnectionError(SolarEdgeError):
    """Network-level failure talking to the API (timeout, DNS, connection)."""


class SolarEdgeApiError(SolarEdgeError):
    """The API returned an unexpected error status."""

    def __init__(self, message: str, *, status: int | None = None,
                 payload: object | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.payload = payload


class SolarEdgeAuthError(SolarEdgeApiError):
    """Authentication failed (HTTP 401/403) — invalid or missing API key."""


class SolarEdgeNotFoundError(SolarEdgeApiError):
    """Requested resource or endpoint does not exist (HTTP 404)."""


class SolarEdgeRateLimitError(SolarEdgeApiError):
    """Rate limit exceeded (HTTP 429)."""

    def __init__(self, message: str, *, retry_after: float | None = None,
                 status: int | None = 429, payload: object | None = None) -> None:
        super().__init__(message, status=status, payload=payload)
        self.retry_after = retry_after
