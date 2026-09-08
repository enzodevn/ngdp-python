"""Controlled analytical access to CSV and PostgreSQL data backends."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

try:
    from .config import PROCESSED_DATA_PATH, RAW_DATA_PATH, SOURCE_METADATA_PATH
    from .data_loading import EnergyDataError, load_energy_data
    from .database import (
        DatabaseReadError,
        DatabaseSettings,
        DatabaseSyncError,
        connect_database,
        load_current_generation,
        prepare_database_snapshot,
    )
    from .provenance import SourceMetadataError, validate_raw_snapshot
except ImportError:  # Supports direct execution from the src directory.
    from config import PROCESSED_DATA_PATH, RAW_DATA_PATH, SOURCE_METADATA_PATH
    from data_loading import EnergyDataError, load_energy_data
    from database import (
        DatabaseReadError,
        DatabaseSettings,
        DatabaseSyncError,
        connect_database,
        load_current_generation,
        prepare_database_snapshot,
    )
    from provenance import SourceMetadataError, validate_raw_snapshot


DATA_BACKEND_ENV_VAR = "NGDP_DATA_BACKEND"
CSV_BACKEND = "csv"
POSTGRESQL_BACKEND = "postgresql"
SUPPORTED_BACKENDS = frozenset({CSV_BACKEND, POSTGRESQL_BACKEND})


class DataAccessError(RuntimeError):
    """Raised when an analytical backend cannot provide trusted data."""


class DataBackendConfigurationError(DataAccessError):
    """Raised when an unsupported analytical backend is requested."""


class DataParityError(DataAccessError):
    """Raised when PostgreSQL differs from the canonical CSV snapshot."""


@dataclass(frozen=True)
class DataParityReport:
    """Evidence that two analytical datasets represent the same snapshot."""

    processed_sha256: str
    record_count: int
    source_count: int
    period_start: date
    period_end: date
    production_mwh_total: Decimal


@dataclass(frozen=True)
class AnalyticalDataResult:
    """Validated analytical data and the backend that supplied it."""

    data: pd.DataFrame = field(repr=False)
    backend: str
    parity: DataParityReport | None = None


def resolve_data_backend(
    value: str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Resolve an explicit backend or the environment-backed safe default."""

    source = os.environ if environ is None else environ
    candidate = value if value is not None else source.get(DATA_BACKEND_ENV_VAR, "")
    backend = candidate.strip().lower() or CSV_BACKEND
    if backend not in SUPPORTED_BACKENDS:
        supported = ", ".join(sorted(SUPPORTED_BACKENDS))
        raise DataBackendConfigurationError(
            f"{DATA_BACKEND_ENV_VAR} deve usar uma destas opções: {supported}."
        )
    return backend


def verify_data_parity(
    canonical_data: pd.DataFrame,
    candidate_data: pd.DataFrame,
    metadata: Mapping[str, object],
) -> DataParityReport:
    """Verify exact source-period-value parity with the canonical snapshot."""

    try:
        canonical = prepare_database_snapshot(canonical_data, metadata)
        candidate = prepare_database_snapshot(candidate_data, metadata)
    except (DatabaseSyncError, EnergyDataError, KeyError, TypeError) as exc:
        raise DataParityError(
            "O backend candidato não corresponde ao contrato do snapshot canônico."
        ) from exc

    expected_hash = canonical.snapshot.processed_sha256
    if candidate.snapshot.processed_sha256 != expected_hash:
        raise DataParityError(
            "O PostgreSQL diverge do CSV canônico em fonte, período ou valor."
        )

    return DataParityReport(
        processed_sha256=expected_hash,
        record_count=canonical.snapshot.record_count,
        source_count=len(canonical.series),
        period_start=canonical.snapshot.period_start,
        period_end=canonical.snapshot.period_end,
        production_mwh_total=sum(
            (item.production_mwh for item in canonical.observations),
            start=Decimal("0"),
        ),
    )


def load_analytical_data(
    *,
    backend: str | None = None,
    data_path: str | Path = PROCESSED_DATA_PATH,
    raw_path: str | Path = RAW_DATA_PATH,
    metadata_path: str | Path = SOURCE_METADATA_PATH,
    settings: DatabaseSettings | None = None,
) -> AnalyticalDataResult:
    """Load trusted analytical data through the configured storage adapter."""

    active_backend = resolve_data_backend(backend)
    canonical_data = load_energy_data(data_path)
    if active_backend == CSV_BACKEND:
        return AnalyticalDataResult(data=canonical_data, backend=CSV_BACKEND)

    try:
        metadata = validate_raw_snapshot(raw_path, metadata_path)
        with connect_database(settings) as connection:
            database_data = load_current_generation(
                connection,
                provider=str(metadata["provider"]),
                table_id=str(metadata["table_id"]),
            )
    except (DatabaseReadError, SourceMetadataError, OSError, KeyError) as exc:
        raise DataAccessError(
            "Não foi possível carregar um snapshot PostgreSQL confiável."
        ) from exc
    except Exception as exc:
        raise DataAccessError("Não foi possível acessar o PostgreSQL.") from exc

    parity = verify_data_parity(canonical_data, database_data, metadata)
    return AnalyticalDataResult(
        data=database_data,
        backend=POSTGRESQL_BACKEND,
        parity=parity,
    )
