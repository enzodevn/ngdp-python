"""NGDP command-line pipeline."""

import argparse
from pathlib import Path

try:
    from .analytics import calculate_statistics
    from .config import (
        PROCESSED_DATA_PATH,
        RAW_DATA_PATH,
        REPORT_PATH,
        SOURCE_METADATA_PATH,
    )
    from .data_cleaning import clean_energy_data
    from .data_loading import load_energy_data
    from .database import connect_database, synchronize_current_snapshot
    from .ingestion import (
        UpdateSummary,
        apply_official_update,
        prepare_official_update,
    )
    from .provenance import validate_raw_snapshot
    from .reporting import generate_report, save_report
except ImportError:  # Supports direct execution from the src directory.
    from analytics import calculate_statistics
    from config import (
        PROCESSED_DATA_PATH,
        RAW_DATA_PATH,
        REPORT_PATH,
        SOURCE_METADATA_PATH,
    )
    from data_cleaning import clean_energy_data
    from data_loading import load_energy_data
    from database import connect_database, synchronize_current_snapshot
    from ingestion import (
        UpdateSummary,
        apply_official_update,
        prepare_official_update,
    )
    from provenance import validate_raw_snapshot
    from reporting import generate_report, save_report


def run_pipeline(
    *,
    raw_data_path: str | Path = RAW_DATA_PATH,
    source_metadata_path: str | Path = SOURCE_METADATA_PATH,
    data_path: str | Path = PROCESSED_DATA_PATH,
    report_path: str | Path = REPORT_PATH,
    rebuild_data: bool = False,
    update_from_api: bool = False,
    sync_database: bool = False,
    show_charts: bool = True,
) -> Path:
    """Run transformation, loading, analytics, reporting and visualization."""

    if update_from_api:
        prepared_update = prepare_official_update(
            raw_path=raw_data_path,
            processed_path=data_path,
            metadata_path=source_metadata_path,
        )
        print_update_summary(prepared_update.summary)
        apply_official_update(
            prepared_update,
            raw_path=raw_data_path,
            processed_path=data_path,
            metadata_path=source_metadata_path,
        )
    elif rebuild_data:
        validate_raw_snapshot(raw_data_path, source_metadata_path)
        clean_energy_data(raw_data_path, data_path)

    df = load_energy_data(data_path)

    if sync_database:
        with connect_database() as connection:
            sync_result = synchronize_current_snapshot(
                connection,
                raw_path=raw_data_path,
                data_path=data_path,
                metadata_path=source_metadata_path,
            )
        print(
            "PostgreSQL sincronizado: "
            f"{sync_result.observation_count} observações, "
            f"snapshot {sync_result.snapshot_id}."
        )

    stats = calculate_statistics(df)
    report = generate_report(stats)
    saved_report = save_report(report, report_path)

    print(report)
    print(f"Relatório salvo em: {saved_report}")

    if show_charts:
        try:
            from .visualization import show_production_charts
        except ImportError:
            from visualization import show_production_charts

        show_production_charts(df)

    return saved_report


def print_update_summary(summary: UpdateSummary) -> None:
    """Print an auditable summary of differences found in the official data."""

    print("===== NGDP SOURCE UPDATE =====")
    print(f"Período local: {summary.old_period_end}")
    print(f"Período oficial: {summary.new_period_end}")
    print(f"Novas observações: {summary.added_rows}")
    print(f"Revisões oficiais: {summary.revised_rows}")
    print(f"Remoções detectadas: {summary.removed_rows}")
    if not summary.changed:
        print("O snapshot local já está atualizado.")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""

    parser = argparse.ArgumentParser(
        description="Executa o pipeline analítico do NGDP.",
    )
    parser.add_argument(
        "--raw-data",
        type=Path,
        default=RAW_DATA_PATH,
        help="Caminho do snapshot CSV bruto.",
    )
    parser.add_argument(
        "--source-metadata",
        type=Path,
        default=SOURCE_METADATA_PATH,
        help="Caminho dos metadados JSON do snapshot bruto.",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=PROCESSED_DATA_PATH,
        help="Caminho do CSV processado.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=REPORT_PATH,
        help="Caminho de saída do relatório.",
    )
    source_action = parser.add_mutually_exclusive_group()
    source_action.add_argument(
        "--rebuild-data",
        action="store_true",
        help="Reconstrói o CSV processado a partir do snapshot bruto.",
    )
    source_action.add_argument(
        "--check-updates",
        action="store_true",
        help="Consulta a fonte oficial e mostra diferenças sem alterar arquivos.",
    )
    source_action.add_argument(
        "--update-from-api",
        action="store_true",
        help="Atualiza e valida o snapshot usando a API oficial.",
    )
    parser.add_argument(
        "--sync-database",
        action="store_true",
        help="Aplica migrations e sincroniza o snapshot com o PostgreSQL.",
    )
    parser.add_argument(
        "--no-charts",
        action="store_true",
        help="Executa o pipeline sem abrir gráficos.",
    )
    return parser


def main() -> None:
    """Execute the NGDP command-line interface."""

    args = build_parser().parse_args()
    if args.check_updates:
        prepared_update = prepare_official_update(
            raw_path=args.raw_data,
            processed_path=args.data,
            metadata_path=args.source_metadata,
        )
        print_update_summary(prepared_update.summary)
        return

    run_pipeline(
        raw_data_path=args.raw_data,
        source_metadata_path=args.source_metadata,
        data_path=args.data,
        report_path=args.report,
        rebuild_data=args.rebuild_data,
        update_from_api=args.update_from_api,
        sync_database=args.sync_database,
        show_charts=not args.no_charts,
    )


if __name__ == "__main__":
    main()
