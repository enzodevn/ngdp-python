"""Central project paths used by the NGDP pipeline."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DATA_PATH = PROJECT_ROOT / "data_raw" / "norway_energy_raw.csv"
PROCESSED_DATA_PATH = (
    PROJECT_ROOT / "data_processed" / "norway_energy_cleaned.csv"
)

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
REPORT_PATH = OUTPUTS_DIR / "ngdp_report.txt"

LEGACY_DATA_PATH = PROJECT_ROOT / "data" / "energy_data.csv"
