"""Tests for controlled analytical backend adoption."""

from decimal import Decimal

import pandas as pd
import pytest

from src.data_access import (
    CSV_BACKEND,
    POSTGRESQL_BACKEND,
    DataBackendConfigurationError,
    DataParityError,
    load_analytical_data,
    resolve_data_backend,
    verify_data_parity,
)
from src.data_loading import load_energy_data
from src.provenance import load_source_metadata


def test_csv_is_the_default_analytical_backend() -> None:
    assert resolve_data_backend(environ={}) == CSV_BACKEND


def test_backend_can_be_selected_from_environment() -> None:
    backend = resolve_data_backend(environ={"NGDP_DATA_BACKEND": " PostgreSQL "})

    assert backend == POSTGRESQL_BACKEND


def test_unsupported_backend_is_rejected() -> None:
    with pytest.raises(DataBackendConfigurationError, match="csv, postgresql"):
        resolve_data_backend("sqlite")


def test_matching_candidate_passes_the_parity_gate() -> None:
    canonical = load_energy_data()

    report = verify_data_parity(
        canonical,
        canonical.sample(frac=1, random_state=7),
        load_source_metadata(),
    )

    assert report.record_count == 1216
    assert report.source_count == 4
    assert report.period_start.isoformat() == "1993-01-01"
    assert report.period_end.isoformat() == "2026-07-01"
    assert report.production_mwh_total == Decimal("4519175624")
    assert len(report.processed_sha256) == 64


def test_changed_candidate_is_blocked_by_the_parity_gate() -> None:
    canonical = load_energy_data()
    changed = canonical.copy()
    changed.loc[0, "production_mwh"] += 1

    with pytest.raises(DataParityError, match="diverge"):
        verify_data_parity(canonical, changed, load_source_metadata())


def test_postgresql_backend_returns_only_verified_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canonical = load_energy_data()

    class FakeConnection:
        def __enter__(self) -> object:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(
        "src.data_access.connect_database",
        lambda settings=None: FakeConnection(),
    )
    monkeypatch.setattr(
        "src.data_access.load_current_generation",
        lambda connection, **identity: canonical.copy(),
    )

    result = load_analytical_data(backend=POSTGRESQL_BACKEND)

    assert result.backend == POSTGRESQL_BACKEND
    assert result.parity is not None
    pd.testing.assert_frame_equal(result.data, canonical)
