"""PostgreSQL integration test executed by the database CI job."""

import os
from decimal import Decimal

import pytest

from src.database import (
    DatabaseSettings,
    connect_database,
    synchronize_current_snapshot,
)

TEST_DATABASE_URL = os.environ.get("NGDP_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="NGDP_TEST_DATABASE_URL is available only in the PostgreSQL CI job.",
)


def test_current_snapshot_is_loaded_idempotently() -> None:
    settings = DatabaseSettings.from_url(TEST_DATABASE_URL or "")

    with connect_database(settings) as connection:
        first_result = synchronize_current_snapshot(connection)
        second_result = synchronize_current_snapshot(connection)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*),
                    MIN(period_start),
                    MAX(period_start),
                    SUM(production_mwh),
                    COUNT(DISTINCT energy_source)
                FROM ngdp.current_generation
                WHERE provider = %s AND table_id = %s
                """,
                ("Statistics Norway", "14091"),
            )
            row_count, period_start, period_end, total_mwh, source_count = (
                cursor.fetchone()
            )
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM ngdp.source_snapshot AS snapshot
                JOIN ngdp.dataset_source AS source
                    ON source.source_id = snapshot.source_id
                WHERE source.provider = %s AND source.table_id = %s
                """,
                ("Statistics Norway", "14091"),
            )
            snapshot_count = cursor.fetchone()[0]

    assert first_result.snapshot_id == second_result.snapshot_id
    assert first_result.observation_count == 1216
    assert second_result.observation_count == 1216
    assert second_result.snapshot_created is False
    assert snapshot_count == 1
    assert row_count == 1216
    assert source_count == 4
    assert total_mwh == Decimal("4519175624.000")
    assert period_start.isoformat() == "1993-01-01"
    assert period_end.isoformat() == "2026-07-01"
