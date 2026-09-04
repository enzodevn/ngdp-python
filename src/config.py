"""Central project paths used by the NGDP pipeline."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ASSETS_DIR = PROJECT_ROOT / "assets"
DASHBOARD_STYLE_PATH = ASSETS_DIR / "dashboard.css"

RAW_DATA_PATH = PROJECT_ROOT / "data_raw" / "norway_energy_raw.csv"
SOURCE_METADATA_PATH = PROJECT_ROOT / "data_raw" / "source.json"
PROCESSED_DATA_PATH = PROJECT_ROOT / "data_processed" / "norway_energy_cleaned.csv"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
REPORT_PATH = OUTPUTS_DIR / "ngdp_report.txt"

LEGACY_DATA_PATH = PROJECT_ROOT / "data" / "energy_data.csv"
