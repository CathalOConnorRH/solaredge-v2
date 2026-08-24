"""Shared test fixtures.

Instead of monkeypatching aiohttp (fragile across versions), we use a tiny fake
session that implements only the surface the client actually uses:
``session.get(...)`` returning an async-context-manager response with
``.status``, ``.headers``, ``.url``, ``.json()`` and ``.text()``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from multidict import CIMultiDict
from yarl import URL

FIXTURES = Path(__file__).parent / "fixtures"
BASE_URL = "https://monitoringapi.solaredge.com/v2"


def load_fixture(name: str) -> Any:
    """Load a captured JSON fixture by file name (without extension)."""
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


class FakeResponse:
    def __init__(self, status: int, payload: Any, headers: dict[str, str] | None,
                 url: str) -> None:
        self.status = status
        self._payload = payload
        self.headers = CIMultiDict(headers or {})
        self.url = URL(url)

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    async def json(self) -> Any:
        return self._payload

    async def text(self) -> str:
        return json.dumps(self._payload)


class FakeSession:
    """Minimal stand-in for aiohttp.ClientSession used by the client."""

    def __init__(self) -> None:
        self.routes: dict[str, tuple[int, Any, dict[str, str] | None]] = {}
        self.requests: list[dict[str, Any]] = []

    def add(self, path: str, *, status: int = 200, payload: Any = None,
            headers: dict[str, str] | None = None) -> None:
        self.routes[f"{BASE_URL}{path}"] = (status, payload, headers)

    def get(self, url: str, *, headers: dict[str, str] | None = None,
            params: dict[str, Any] | None = None, timeout: Any = None) -> FakeResponse:
        self.requests.append({"url": url, "params": params, "headers": headers})
        if url not in self.routes:
            raise AssertionError(f"unexpected request to {url}")
        status, payload, resp_headers = self.routes[url]
        return FakeResponse(status, payload, resp_headers, url)


@pytest.fixture
def session() -> FakeSession:
    return FakeSession()
