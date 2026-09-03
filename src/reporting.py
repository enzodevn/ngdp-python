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
        f"Produção Total: {stats['total']:.2f} MWh\n"
        f"Produção Média por Registro: {stats['media']:.2f} MWh\n"
        f"Produção Máxima por Registro: {stats['maximo']:.2f} MWh\n"
        f"Produção Mínima por Registro: {stats['minimo']:.2f} MWh\n"
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
