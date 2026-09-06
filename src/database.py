"""PostgreSQL persistence for validated NGDP source snapshots."""

from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd

try:
    from .config import (
        DATABASE_MIGRATIONS_DIR,
        PROCESSED_DATA_PATH,
        RAW_DATA_PATH,
        SOURCE_METADATA_PATH,
    )
    from .data_loading import load_energy_data
    from .provenance import validate_raw_snapshot
except ImportError:  # Supports direct execution from the src directory.
    from config import (
        DATABASE_MIGRATIONS_DIR,
        PROCESSED_DATA_PATH,
        RAW_DATA_PATH,
        SOURCE_METADATA_PATH,
    )
    from data_loading import load_energy_data
    from provenance import validate_raw_snapshot


DATABASE_URL_ENV_VAR = "NGDP_DATABASE_URL"
MIGRATION_FILE_PATTERN = re.compile(r"^(?P<version>\d{3})_[a-z0-9_]+\.sql$")
SOURCE_SERIES_PATTERN = re.compile(r"^(?P<code>\d+(?:\.\d+)*)\s+(?P<name>.+)$")


class DatabaseConfigurationError(ValueError):
    """Raised when database connection settings are missing or invalid."""


class DatabaseMigrationError(RuntimeError):
    """Raised when a database migration cannot be trusted or applied."""


class DatabaseSyncError(RuntimeError):
    """Raised when a validated snapshot cannot be synchronized safely."""


@dataclass(frozen=True)
class DatabaseSettings:
    """Validated PostgreSQL settings without exposing credentials in repr output."""

    url: str = field(repr=False)

    @classmethod
    def from_url(cls, value: str) -> DatabaseSettings:
        """Validate an explicit PostgreSQL connection URL."""

        candidate = value.strip()
        parsed = urlparse(candidate)
        if parsed.scheme not in {"postgres", "postgresql"}:
            raise DatabaseConfigurationError(
                "NGDP_DATABASE_URL deve usar o protocolo postgresql://."
            )
        if not parsed.hostname or not parsed.path.strip("/"):
            raise DatabaseConfigurationError(
                "NGDP_DATABASE_URL deve informar servidor e banco de dados."
            )
        return cls(url=candidate)

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> DatabaseSettings:
        """Read the database URL from the process environment."""

        source = os.environ if environ is None else environ
        value = source.get(DATABASE_URL_ENV_VAR, "")
        if not value.strip():
            raise DatabaseConfigurationError(
                f"Defina {DATABASE_URL_ENV_VAR} antes de sincronizar o PostgreSQL."
            )
        return cls.from_url(value)


@dataclass(frozen=True)
class Migration:
    """One immutable, checksummed SQL migration."""

    version: str
    name: str
    checksum: str
    sql: str


@dataclass(frozen=True)
class SourceDescriptor:
    """Stable identity and provenance fields for one official dataset."""

    provider: str
    table_id: str
    title: str
    table_url: str
    api_url: str
    unit: str
    frequency: str
    license_identifier: str
    license_url: str


@dataclass(frozen=True)
class SnapshotDescriptor:
    """Version and coverage fields for one immutable source snapshot."""

    raw_sha256: str
    processed_sha256: str
    retrieved_at: datetime
    source_updated_at: datetime | None
    verified_on: date
    period_start: date
    period_end: date
    record_count: int


@dataclass(frozen=True)
class EnergySeries:
    """Provider code and normalized label for one generation series."""

    source_code: str
    name: str


@dataclass(frozen=True)
class Observation:
    """One monthly production value ready for relational persistence."""

    source_code: str
    period_start: date
    production_mwh: Decimal


@dataclass(frozen=True)
class PreparedSnapshot:
    """Validated database payload derived from canonical NGDP files."""

    source: SourceDescriptor
    snapshot: SnapshotDescriptor
    series: tuple[EnergySeries, ...]
    observations: tuple[Observation, ...]


@dataclass(frozen=True)
class DatabaseSyncResult:
    """Auditable result of a migration and snapshot synchronization."""

    migrations_applied: tuple[str, ...]
    snapshot_id: int
    snapshot_created: bool
    source_count: int
    observation_count: int


def discover_migrations(
    directory: str | Path = DATABASE_MIGRATIONS_DIR,
) -> tuple[Migration, ...]:
    """Load ordered SQL migrations and calculate their SHA-256 checksums."""

    migration_dir = Path(directory)
    if not migration_dir.is_dir():
        raise DatabaseMigrationError(
            f"Diretório de migrations não encontrado: {migration_dir}"
        )

    migrations: list[Migration] = []
    versions: set[str] = set()
    for path in sorted(migration_dir.glob("*.sql")):
        match = MIGRATION_FILE_PATTERN.fullmatch(path.name)
        if match is None:
            raise DatabaseMigrationError(f"Nome de migration inválido: {path.name}")

        version = match.group("version")
        if version in versions:
            raise DatabaseMigrationError(f"Versão de migration duplicada: {version}")

        sql = path.read_text(encoding="utf-8").strip()
        if not sql:
            raise DatabaseMigrationError(f"Migration vazia: {path.name}")

        versions.add(version)
        migrations.append(
            Migration(
                version=version,
                name=path.stem,
                checksum=hashlib.sha256(sql.encode("utf-8")).hexdigest(),
                sql=sql,
            )
        )

    if not migrations:
        raise DatabaseMigrationError("Nenhuma migration SQL foi encontrada.")

    return tuple(migrations)


def connect_database(settings: DatabaseSettings | None = None) -> Any:
    """Open a Psycopg connection using validated settings."""

    active_settings = settings or DatabaseSettings.from_env()
    try:
        import psycopg
    except ModuleNotFoundError as exc:
        raise DatabaseConfigurationError(
            "O driver PostgreSQL não está instalado. Reinstale requirements.txt."
        ) from exc

    return psycopg.connect(active_settings.url)


def apply_migrations(
    connection: Any,
    directory: str | Path = DATABASE_MIGRATIONS_DIR,
) -> tuple[str, ...]:
    """Apply pending migrations and reject changes to applied SQL files."""

    migrations = discover_migrations(directory)
    applied_now: list[str] = []

    with connection.transaction(), connection.cursor() as cursor:
        cursor.execute("CREATE SCHEMA IF NOT EXISTS ngdp")
        cursor.execute(
            """
                CREATE TABLE IF NOT EXISTS ngdp.schema_migration (
                    version TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT schema_migration_hash_format
                        CHECK (checksum ~ '^[0-9a-f]{64}$')
                )
                """
        )
        cursor.execute("SELECT version, checksum FROM ngdp.schema_migration")
        applied = {str(row[0]): str(row[1]) for row in cursor.fetchall()}

        for migration in migrations:
            recorded_checksum = applied.get(migration.version)
            if recorded_checksum is not None:
                if recorded_checksum != migration.checksum:
                    raise DatabaseMigrationError(
                        f"Migration já aplicada foi alterada: {migration.name}"
                    )
                continue

            cursor.execute(migration.sql, prepare=False)
            cursor.execute(
                """
                    INSERT INTO ngdp.schema_migration (
                        version,
                        name,
                        checksum
                    )
                    VALUES (%s, %s, %s)
                    """,
                (migration.version, migration.name, migration.checksum),
            )
            applied_now.append(migration.name)

    return tuple(applied_now)


def prepare_database_snapshot(
    data: pd.DataFrame,
    metadata: Mapping[str, Any],
) -> PreparedSnapshot:
    """Convert validated canonical data and provenance into a database batch."""

    snapshot_data = metadata["snapshot"]
    license_data = metadata["license"]
    record_count = _positive_integer(snapshot_data.get("record_count"), "record_count")

    if record_count != len(data):
        raise DatabaseSyncError(
            "A contagem do snapshot não corresponde ao dataset processado."
        )

    series = _parse_energy_series(metadata.get("selected_series"))
    names_by_code = {item.source_code: item.name for item in series}
    codes_by_name = {item.name: item.source_code for item in series}
    data_sources = set(data["energy_source"].astype(str))
    if data_sources != set(codes_by_name):
        raise DatabaseSyncError(
            "As séries processadas não correspondem às séries da proveniência."
        )

    period_start = _parse_month(snapshot_data.get("period_start"), "period_start")
    period_end = _parse_month(snapshot_data.get("period_end"), "period_end")
    actual_start = data["date"].min().date()
    actual_end = data["date"].max().date()
    if (actual_start, actual_end) != (period_start, period_end):
        raise DatabaseSyncError(
            "O período do snapshot não corresponde ao dataset processado."
        )

    observations = tuple(
        sorted(
            (
                Observation(
                    source_code=codes_by_name[str(row.energy_source)],
                    period_start=row.date.date(),
                    production_mwh=Decimal(str(row.production_mwh)),
                )
                for row in data.itertuples(index=False)
            ),
            key=lambda item: (item.period_start, item.source_code),
        )
    )

    source = SourceDescriptor(
        provider=str(metadata["provider"]),
        table_id=str(metadata["table_id"]),
        title=str(metadata["title"]),
        table_url=str(metadata["table_url"]),
        api_url=str(metadata["api_url"]),
        unit=str(metadata["unit"]),
        frequency=str(metadata["frequency"]),
        license_identifier=str(license_data["identifier"]),
        license_url=str(license_data["url"]),
    )
    snapshot = SnapshotDescriptor(
        raw_sha256=str(snapshot_data["raw_sha256"]).lower(),
        processed_sha256=_observation_checksum(observations),
        retrieved_at=_parse_timestamp(
            snapshot_data.get("retrieved_on"),
            "retrieved_on",
        ),
        source_updated_at=_parse_optional_timestamp(
            snapshot_data.get("source_updated_at"),
            "source_updated_at",
        ),
        verified_on=_parse_date(snapshot_data.get("verified_on"), "verified_on"),
        period_start=period_start,
        period_end=period_end,
        record_count=record_count,
    )

    if len(names_by_code) != len(series):
        raise DatabaseSyncError("A proveniência contém códigos de série duplicados.")

    return PreparedSnapshot(
        source=source,
        snapshot=snapshot,
        series=series,
        observations=observations,
    )


def synchronize_current_snapshot(
    connection: Any,
    *,
    raw_path: str | Path = RAW_DATA_PATH,
    data_path: str | Path = PROCESSED_DATA_PATH,
    metadata_path: str | Path = SOURCE_METADATA_PATH,
    migrations_dir: str | Path = DATABASE_MIGRATIONS_DIR,
) -> DatabaseSyncResult:
    """Apply migrations and synchronize the current canonical snapshot."""

    metadata = validate_raw_snapshot(raw_path, metadata_path)
    data = load_energy_data(data_path)
    prepared = prepare_database_snapshot(data, metadata)
    migrations_applied = apply_migrations(connection, migrations_dir)
    result = _persist_snapshot(connection, prepared)
    return DatabaseSyncResult(
        migrations_applied=migrations_applied,
        snapshot_id=result.snapshot_id,
        snapshot_created=result.snapshot_created,
        source_count=result.source_count,
        observation_count=result.observation_count,
    )


def _persist_snapshot(
    connection: Any,
    prepared: PreparedSnapshot,
) -> DatabaseSyncResult:
    source = prepared.source
    snapshot = prepared.snapshot

    with connection.transaction(), connection.cursor() as cursor:
        cursor.execute(
            """
                INSERT INTO ngdp.dataset_source (
                    provider,
                    table_id,
                    title,
                    table_url,
                    api_url,
                    unit,
                    frequency,
                    license_identifier,
                    license_url
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (provider, table_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    table_url = EXCLUDED.table_url,
                    api_url = EXCLUDED.api_url,
                    unit = EXCLUDED.unit,
                    frequency = EXCLUDED.frequency,
                    license_identifier = EXCLUDED.license_identifier,
                    license_url = EXCLUDED.license_url,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING source_id
                """,
            (
                source.provider,
                source.table_id,
                source.title,
                source.table_url,
                source.api_url,
                source.unit,
                source.frequency,
                source.license_identifier,
                source.license_url,
            ),
        )
        source_id = int(cursor.fetchone()[0])

        cursor.execute(
            """
                INSERT INTO ngdp.source_snapshot (
                    source_id,
                    raw_sha256,
                    processed_sha256,
                    retrieved_at,
                    source_updated_at,
                    verified_on,
                    period_start,
                    period_end,
                    record_count
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (
                    source_id,
                    raw_sha256,
                    processed_sha256
                ) DO NOTHING
                RETURNING snapshot_id
                """,
            (
                source_id,
                snapshot.raw_sha256,
                snapshot.processed_sha256,
                snapshot.retrieved_at,
                snapshot.source_updated_at,
                snapshot.verified_on,
                snapshot.period_start,
                snapshot.period_end,
                snapshot.record_count,
            ),
        )
        inserted_snapshot = cursor.fetchone()
        snapshot_created = inserted_snapshot is not None
        if inserted_snapshot is None:
            cursor.execute(
                """
                    SELECT snapshot_id, record_count
                    FROM ngdp.source_snapshot
                    WHERE source_id = %s
                        AND raw_sha256 = %s
                        AND processed_sha256 = %s
                    """,
                (
                    source_id,
                    snapshot.raw_sha256,
                    snapshot.processed_sha256,
                ),
            )
            existing = cursor.fetchone()
            if existing is None or int(existing[1]) != snapshot.record_count:
                raise DatabaseSyncError(
                    "O snapshot existente não corresponde à proveniência atual."
                )
            snapshot_id = int(existing[0])
        else:
            snapshot_id = int(inserted_snapshot[0])

        source_ids: dict[str, int] = {}
        for series in prepared.series:
            cursor.execute(
                """
                    INSERT INTO ngdp.energy_source (
                        source_id,
                        source_code,
                        name
                    )
                    VALUES (%s, %s, %s)
                    ON CONFLICT (source_id, source_code) DO UPDATE SET
                        name = EXCLUDED.name,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING energy_source_id
                    """,
                (source_id, series.source_code, series.name),
            )
            source_ids[series.source_code] = int(cursor.fetchone()[0])

        if snapshot_created:
            cursor.executemany(
                """
                INSERT INTO ngdp.generation_observation (
                    snapshot_id,
                    energy_source_id,
                    period_start,
                    production_mwh
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    (
                        snapshot_id,
                        source_ids[item.source_code],
                        item.period_start,
                        item.production_mwh,
                    )
                    for item in prepared.observations
                ),
            )
        cursor.execute(
            """
                SELECT COUNT(*)
                FROM ngdp.generation_observation
                WHERE snapshot_id = %s
                """,
            (snapshot_id,),
        )
        observation_count = int(cursor.fetchone()[0])
        if observation_count != snapshot.record_count:
            raise DatabaseSyncError(
                "A carga PostgreSQL terminou com uma contagem inesperada."
            )

    return DatabaseSyncResult(
        migrations_applied=(),
        snapshot_id=snapshot_id,
        snapshot_created=snapshot_created,
        source_count=len(source_ids),
        observation_count=observation_count,
    )


def _parse_energy_series(value: Any) -> tuple[EnergySeries, ...]:
    if not isinstance(value, list) or not value:
        raise DatabaseSyncError("A proveniência não contém selected_series.")

    series: list[EnergySeries] = []
    for raw_item in value:
        match = SOURCE_SERIES_PATTERN.fullmatch(str(raw_item).strip())
        if match is None:
            raise DatabaseSyncError(f"Série sem código oficial válido: {raw_item}")
        series.append(
            EnergySeries(
                source_code=match.group("code"),
                name=match.group("name").strip(),
            )
        )

    codes = {item.source_code for item in series}
    names = {item.name for item in series}
    if len(codes) != len(series) or len(names) != len(series):
        raise DatabaseSyncError("A proveniência contém séries duplicadas.")
    return tuple(series)


def _observation_checksum(observations: tuple[Observation, ...]) -> str:
    digest = hashlib.sha256()
    for item in observations:
        normalized_value = format(item.production_mwh.normalize(), "f")
        line = (
            f"{item.source_code}|{item.period_start.isoformat()}|{normalized_value}\n"
        )
        digest.update(line.encode("utf-8"))
    return digest.hexdigest()


def _positive_integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise DatabaseSyncError(f"{field_name} deve ser um inteiro positivo.")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise DatabaseSyncError(f"{field_name} deve ser um inteiro positivo.") from exc
    if parsed <= 0:
        raise DatabaseSyncError(f"{field_name} deve ser um inteiro positivo.")
    return parsed


def _parse_month(value: Any, field_name: str) -> date:
    try:
        return datetime.strptime(str(value), "%YM%m").date()
    except (TypeError, ValueError) as exc:
        raise DatabaseSyncError(
            f"{field_name} deve usar o formato mensal YYYYMmm."
        ) from exc


def _parse_date(value: Any, field_name: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise DatabaseSyncError(f"{field_name} deve ser uma data ISO válida.") from exc


def _parse_timestamp(value: Any, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise DatabaseSyncError(
            f"{field_name} deve ser um timestamp ISO válido."
        ) from exc
    if parsed.tzinfo is None:
        raise DatabaseSyncError(f"{field_name} deve informar o fuso horário.")
    return parsed


def _parse_optional_timestamp(value: Any, field_name: str) -> datetime | None:
    if value in {None, ""}:
        return None
    return _parse_timestamp(value, field_name)
