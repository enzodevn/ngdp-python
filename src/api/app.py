"""FastAPI entry point for the first NGDP V3 API slice."""

from fastapi import FastAPI, HTTPException, status

from ..data_access import DataAccessError
from .models import EnergySummaryResponse, HealthResponse
from .service import build_energy_summary

app = FastAPI(
    title="NGDP API",
    description="Read-only access to validated Norwegian energy analytics.",
    version="0.1.0",
)


@app.get("/health", response_model=HealthResponse, tags=["operations"])
def health() -> HealthResponse:
    """Report whether the API process is ready to answer requests."""

    return HealthResponse()


@app.get(
    "/api/v1/energy/summary",
    response_model=EnergySummaryResponse,
    tags=["energy"],
)
def energy_summary() -> EnergySummaryResponse:
    """Expose indicators derived from the trusted analytical snapshot."""

    try:
        return build_energy_summary()
    except (DataAccessError, OSError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The validated NGDP snapshot is temporarily unavailable.",
        ) from exc
