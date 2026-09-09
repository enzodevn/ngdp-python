"""Application services that translate trusted data into API contracts."""

from __future__ import annotations

from ..analytics import calculate_statistics
from ..data_access import AnalyticalDataResult, load_analytical_data
from .models import EnergySummaryResponse


def build_energy_summary(
    result: AnalyticalDataResult | None = None,
) -> EnergySummaryResponse:
    """Build a versioned summary from the controlled analytical gateway."""

    analytical_result = result or load_analytical_data()
    statistics = calculate_statistics(analytical_result.data)

    return EnergySummaryResponse(
        backend=analytical_result.backend,
        record_count=len(analytical_result.data),
        source_count=statistics["source_count"],
        month_count=statistics["month_count"],
        period_start=statistics["period_start"],
        period_end=statistics["period_end"],
        total_mwh=statistics["total_mwh"],
        latest_month_mwh=statistics["latest_month_mwh"],
    )
