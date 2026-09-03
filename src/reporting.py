"""Text report generation for NGDP analytics."""

from pathlib import Path

try:
    from .analytics import EnergyStatistics
    from .config import REPORT_PATH
except ImportError:  # Supports direct imports from the src directory.
    from analytics import EnergyStatistics
    from config import REPORT_PATH


def generate_report(stats: EnergyStatistics) -> str:
    """Format analytical statistics as a human-readable report."""

    return (
        "===== NGDP REPORT =====\n\n"
        f"Período: {stats['period_start']} a {stats['period_end']}\n"
        f"Meses analisados: {stats['month_count']}\n"
        f"Fontes analisadas: {stats['source_count']}\n\n"
        f"Produção acumulada: {stats['total_mwh']:.2f} MWh\n"
        "Produção média mensal combinada: "
        f"{stats['monthly_average_mwh']:.2f} MWh\n"
        f"Pico mensal combinado: {stats['monthly_peak_mwh']:.2f} MWh\n"
        "Mínimo mensal combinado: "
        f"{stats['monthly_minimum_mwh']:.2f} MWh\n"
        "Produção no mês mais recente: "
        f"{stats['latest_month_mwh']:.2f} MWh\n"
    )


def save_report(
    report_text: str,
    output_path: str | Path = REPORT_PATH,
) -> Path:
    """Save a report, creating its output directory when necessary."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report_text, encoding="utf-8")
    return path
