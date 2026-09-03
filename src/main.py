"""NGDP command-line pipeline."""

import argparse
from pathlib import Path

try:
    from .analytics import calculate_statistics
    from .config import PROCESSED_DATA_PATH, REPORT_PATH
    from .data_loading import load_energy_data
    from .reporting import generate_report, save_report
except ImportError:  # Supports direct execution from the src directory.
    from analytics import calculate_statistics
    from config import PROCESSED_DATA_PATH, REPORT_PATH
    from data_loading import load_energy_data
    from reporting import generate_report, save_report


def run_pipeline(
    *,
    data_path: str | Path = PROCESSED_DATA_PATH,
    report_path: str | Path = REPORT_PATH,
    show_charts: bool = True,
) -> Path:
    """Run loading, analytics, reporting and optional visualization."""

    df = load_energy_data(data_path)
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


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""

    parser = argparse.ArgumentParser(
        description="Executa o pipeline analítico do NGDP.",
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
    parser.add_argument(
        "--no-charts",
        action="store_true",
        help="Executa o pipeline sem abrir gráficos.",
    )
    return parser


def main() -> None:
    """Execute the NGDP command-line interface."""

    args = build_parser().parse_args()
    run_pipeline(
        data_path=args.data,
        report_path=args.report,
        show_charts=not args.no_charts,
    )


if __name__ == "__main__":
    main()
