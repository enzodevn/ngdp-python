"""FastAPI entry point for the NGDP V3 analytical API."""

from fastapi import Depends, FastAPI, HTTPException, status

from .. import __version__
from ..data_access import DataAccessError, load_analytical_data
from .auth import require_api_token
from .models import EnergySummaryResponse, HealthResponse, ReadinessResponse
from .observability import LOGGER, RequestObservabilityMiddleware
from .service import build_energy_summary

app = FastAPI(
    title="NGDP API",
    description="Read-only access to validated Norwegian energy analytics.",
    version=__version__,
)
app.add_middleware(RequestObservabilityMiddleware, logger=LOGGER)


@app.get("/health", response_model=HealthResponse, tags=["operations"])
def health() -> HealthResponse:
    """Retain the original public process-health contract."""

    return HealthResponse()


@app.get("/health/live", response_model=HealthResponse, tags=["operations"])
def liveness() -> HealthResponse:
    """Report whether the API process is alive."""

    return HealthResponse()


@app.get("/health/ready", response_model=ReadinessResponse, tags=["operations"])
def readiness() -> ReadinessResponse:
    """Prove that the configured analytical backend is ready for requests."""

    try:
        result = load_analytical_data()
    except (DataAccessError, OSError, ValueError) as exc:
        LOGGER.warning(
            "readiness_check_failed",
            extra={"error_type": type(exc).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The configured analytical backend is not ready.",
        ) from exc
    return ReadinessResponse(backend=result.backend)


@app.get(
    "/api/v1/energy/summary",
    response_model=EnergySummaryResponse,
    tags=["energy"],
    dependencies=[Depends(require_api_token)],
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
