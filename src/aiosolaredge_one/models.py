"""Typed models for SolarEdge ONE (Monitoring v2) responses.

Shapes are derived from Phase 0 live captures (see ../prd fixtures). All models
are tolerant of missing/null fields — the API returns nulls freely on sites
without meters or storage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@dataclass(slots=True)
class Site:
    """A site as returned by ``GET /sites``."""

    site_id: int
    name: str | None = None
    peak_power: float | None = None
    installation_date: str | None = None
    location: str | None = None
    activation_status: str | None = None
    note: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def is_active(self) -> bool:
        return (self.activation_status or "").upper() == "ACTIVE"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Site:
        return cls(
            site_id=int(data["siteId"]),
            name=data.get("name"),
            peak_power=_as_float(data.get("peakPower")),
            installation_date=data.get("installationDate"),
            location=data.get("location"),
            activation_status=data.get("activationStatus"),
            note=data.get("note"),
            raw=data,
        )


def parse_site_list(data: dict[str, Any]) -> list[Site]:
    """Parse the nested ``{"sites": {"count": N, "site": [...]}}`` envelope."""
    container = data.get("sites", data)
    if isinstance(container, dict):
        items = container.get("site") or container.get("sites") or []
    elif isinstance(container, list):
        items = container
    else:
        items = []
    return [Site.from_dict(item) for item in items if isinstance(item, dict)]


def parse_site(data: dict[str, Any]) -> Site:
    """Parse a single site from ``GET /sites/{id}`` (may be wrapped in ``site``)."""
    inner = data.get("site")
    if isinstance(inner, dict):
        data = inner
    return Site.from_dict(data)


@dataclass(slots=True)
class ProductionOverview:
    total: float | None = None
    unit: str | None = None
    to_self_consumption: float | None = None
    to_storage: float | None = None
    to_grid: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ProductionOverview:
        data = data or {}
        return cls(
            total=_as_float(data.get("total")),
            unit=data.get("unit"),
            to_self_consumption=_as_float(data.get("toSelfConsumption")),
            to_storage=_as_float(data.get("toStorage")),
            to_grid=_as_float(data.get("toGrid")),
        )


@dataclass(slots=True)
class ConsumptionOverview:
    total: float | None = None
    unit: str | None = None
    from_pv: float | None = None
    from_storage: float | None = None
    from_grid: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ConsumptionOverview:
        data = data or {}
        return cls(
            total=_as_float(data.get("total")),
            unit=data.get("unit"),
            from_pv=_as_float(data.get("fromPv")),
            from_storage=_as_float(data.get("fromStorage")),
            from_grid=_as_float(data.get("fromGrid")),
        )


@dataclass(slots=True)
class SiteOverview:
    """Cumulative lifetime totals from ``GET /sites/{id}/overview``."""

    site_id: int | None
    production: ProductionOverview
    consumption: ConsumptionOverview
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SiteOverview:
        return cls(
            site_id=_as_int(data.get("siteId")),
            production=ProductionOverview.from_dict(data.get("production")),
            consumption=ConsumptionOverview.from_dict(data.get("consumption")),
            raw=data,
        )


@dataclass(slots=True)
class EnvironmentalBenefits:
    """Response of ``GET /sites/{id}/environmental-benefits``.

    v2 trimmed the v1 field set: only ``co2Emissions`` and ``evMiles`` remain
    (``gasEmissionSaved``, ``treesPlanted``, ``lightBulbs`` are gone). Field names
    are best-effort from the migration docs; ``raw`` preserves the full payload.
    """

    co2_emissions: float | None = None
    ev_miles: float | None = None
    unit: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnvironmentalBenefits:
        return cls(
            co2_emissions=_as_float(data.get("co2Emissions")),
            ev_miles=_as_float(data.get("evMiles")),
            unit=data.get("unit"),
            raw=data,
        )


@dataclass(slots=True)
class Device:
    """A device from ``GET /sites/{id}/devices`` (inverter, meter, battery...)."""

    type: str | None = None
    serial_number: str | None = None
    manufacturer: str | None = None
    part_number: str | None = None
    created_at: str | None = None
    firmware_version: str | None = None
    active: bool | None = None
    name: str | None = None
    communication_type: str | None = None
    firmware: str | None = None
    connected_optimizers: int | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Device:
        return cls(
            type=data.get("type"),
            serial_number=data.get("serialNumber"),
            manufacturer=data.get("manufacturer"),
            part_number=data.get("partNumber"),
            created_at=data.get("createdAt"),
            firmware_version=data.get("firmwareVersion"),
            active=data.get("active"),
            name=data.get("name"),
            communication_type=data.get("communicationType"),
            firmware=data.get("firmware"),
            connected_optimizers=_as_int(data.get("connectedOptimizers")),
            raw=data,
        )


def parse_device_list(data: Any) -> list[Device]:
    """Devices may be a bare list or wrapped; be liberal."""
    if isinstance(data, dict):
        for key in ("devices", "device", "data", "items"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        return []
    return [Device.from_dict(item) for item in data if isinstance(item, dict)]


@dataclass(slots=True)
class TimeValue:
    timestamp: str
    value: float | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimeValue:
        return cls(timestamp=data.get("timestamp", ""), value=_as_float(data.get("value")))


@dataclass(slots=True)
class TimeSeries:
    """Response shape of ``/energy`` and ``/power`` (time series of values)."""

    period_from: str | None
    period_to: str | None
    unit: str | None
    resolution: str | None
    values: list[TimeValue] = field(default_factory=list)

    @property
    def non_null_values(self) -> list[TimeValue]:
        return [v for v in self.values if v.value is not None]

    @property
    def latest_value(self) -> float | None:
        """Most recent non-null value (use for 'current power')."""
        for v in reversed(self.values):
            if v.value is not None:
                return v.value
        return None

    @property
    def latest(self) -> TimeValue | None:
        for v in reversed(self.values):
            if v.value is not None:
                return v
        return None

    @property
    def total(self) -> float:
        """Sum of non-null values (e.g. energy accumulated over the period)."""
        return sum(v.value for v in self.values if v.value is not None)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimeSeries:
        period = data.get("period") or {}
        raw_values = data.get("values") or []
        return cls(
            period_from=period.get("from"),
            period_to=period.get("to"),
            unit=data.get("unit"),
            resolution=data.get("resolution"),
            values=[TimeValue.from_dict(v) for v in raw_values if isinstance(v, dict)],
        )
