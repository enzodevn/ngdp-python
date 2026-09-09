"""Versioned response contracts exposed by the NGDP API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Small operational contract used by health checks."""

    model_config = ConfigDict(frozen=True)

    status: Literal["ok"] = "ok"
    service: Literal["ngdp-api"] = "ngdp-api"
    api_version: Literal["v1"] = "v1"


class EnergySummaryResponse(BaseModel):
    """Validated analytical summary for the active NGDP snapshot."""

    model_config = ConfigDict(frozen=True)

    backend: Literal["csv", "postgresql"]
    record_count: int = Field(ge=1)
    source_count: int = Field(ge=1)
    month_count: int = Field(ge=1)
    period_start: str = Field(pattern=r"^\d{4}-\d{2}$")
    period_end: str = Field(pattern=r"^\d{4}-\d{2}$")
    total_mwh: float = Field(ge=0)
    latest_month_mwh: float = Field(ge=0)
