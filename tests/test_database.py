"""Unit tests for the NGDP PostgreSQL foundation."""

from __future__ import annotations

import copy
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.data_loading import load_energy_data
from src.database import (
    DatabaseConfigurationError,
    DatabaseMigrationError,
    DatabaseReadError,
    DatabaseSettings,
    DatabaseSyncError,
    discover_migrations,
    load_current_generation,
    prepare_database_snapshot,
)
from src.provenance import load_source_metadata


class StubCursor:
    """Minimal cursor used to exercise the PostgreSQL read adapter."""

    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows
        self.parameters: tuple[str, str] | None = None

    def __enter__(self) -> StubCursor:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, statement: str, parameters: tuple[str, str]) -> None:
        assert "ngdp.current_generation" in statement
        self.parameters = parameters

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows


class StubConnection:
    """Minimal connection exposing one reusable cursor."""

    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.cursor_instance = StubCursor(rows)

    def cursor(self) -> StubCursor:
        return self.cursor_instance


def test_database_settings_reads_valid_postgresql_url() -> None:
    settings = DatabaseSettings.from_env(
        {"NGDP_DATABASE_URL": "postgresql://ngdp:secret@localhost:5432/ngdp"}
    )

    assert settings.url.endswith("/ngdp")
    assert "secret" not in repr(settings)


def test_load_current_generation_returns_validated_analytical_data() -> None:
    connection = StubConnection(
        [("Hydro power generation", date(2025, 1, 1), Decimal("100.000"))]
    )

    data = load_current_generation(
        connection,
        provider="Statistics Norway",
        table_id="14091",
    )

    assert connection.cursor_instance.parameters == ("Statistics Norway", "14091")
    assert data.loc[0, "date"].isoformat() == "2025-01-01T00:00:00"
    assert data.loc[0, "production_mwh"] == 100


def test_load_current_generation_rejects_missing_snapshot() -> None:
    with pytest.raises(DatabaseReadError, match="não contém"):
        load_current_generation(
            StubConnection([]),
            provider="Statistics Norway",
            table_id="14091",
        )


@pytest.mark.parametrize(
    "environment",
    [
        {},
        {"NGDP_DATABASE_URL": "sqlite:///ngdp.db"},
        {"NGDP_DATABASE_URL": "postgresql:///ngdp"},
        {"NGDP_DATABASE_URL": "postgresql://localhost"},
    ],
)
def test_database_settings_rejects_invalid_configuration(
    environment: dict[str, str],
) -> None:
    with pytest.raises(DatabaseConfigurationError):
        DatabaseSettings.from_env(environment)


def test_discover_migrations_orders_and_checksums_sql(tmp_path: Path) -> None:
    (tmp_path / "002_second.sql").write_text("SELECT 2;", encoding="utf-8")
    (tmp_path / "001_first.sql").write_text("SELECT 1;", encoding="utf-8")

    migrations = discover_migrations(tmp_path)

    assert [item.version for item in migrations] == ["001", "002"]
    assert all(len(item.checksum) == 64 for item in migrations)


def test_discover_migrations_rejects_invalid_filename(tmp_path: Path) -> None:
    (tmp_path / "initial.sql").write_text("SELECT 1;", encoding="utf-8")

    with pytest.raises(DatabaseMigrationError, match="Nome de migration inválido"):
        discover_migrations(tmp_path)


def test_prepare_current_database_snapshot() -> None:
    prepared = prepare_database_snapshot(
        load_energy_data(),
        load_source_metadata(),
    )

    assert prepared.source.table_id == "14091"
    assert prepared.snapshot.record_count == 1216
    assert prepared.snapshot.period_start.isoformat() == "1993-01-01"
    assert prepared.snapshot.period_end.isoformat() == "2026-07-01"
    assert len(prepared.snapshot.processed_sha256) == 64
    assert {item.source_code for item in prepared.series} == {
        "1.1",
        "1.2",
        "1.3",
        "1.4",
    }
    assert len(prepared.observations) == 1216


def test_processed_checksum_changes_with_normalized_content() -> None:
    data = load_energy_data()
    metadata = load_source_metadata()
    original = prepare_database_snapshot(data, metadata)
    changed_data = data.copy()
    changed_data.loc[0, "production_mwh"] += 1

    changed = prepare_database_snapshot(changed_data, metadata)

    assert changed.snapshot.raw_sha256 == original.snapshot.raw_sha256
    assert changed.snapshot.processed_sha256 != original.snapshot.processed_sha256


def test_processed_checksum_is_independent_of_row_order() -> None:
    data = load_energy_data()
    metadata = load_source_metadata()

    original = prepare_database_snapshot(data, metadata)
    reordered = prepare_database_snapshot(data.iloc[::-1], metadata)

    assert reordered.snapshot.processed_sha256 == original.snapshot.processed_sha256


def test_prepare_snapshot_rejects_provenance_count_mismatch() -> None:
    metadata = copy.deepcopy(load_source_metadata())
    metadata["snapshot"]["record_count"] = 1

    with pytest.raises(DatabaseSyncError, match="contagem"):
        prepare_database_snapshot(load_energy_data(), metadata)
