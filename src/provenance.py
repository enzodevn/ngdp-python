"""Load and verify provenance metadata for the NGDP source snapshot."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

try:
    from .config import RAW_DATA_PATH, SOURCE_METADATA_PATH
except ImportError:  # Supports direct execution from the src directory.
    from config import RAW_DATA_PATH, SOURCE_METADATA_PATH


REQUIRED_METADATA_FIELDS = {
    "provider",
    "table_id",
    "title",
    "table_url",
    "api_url",
    "unit",
    "frequency",
    "license",
    "snapshot",
}
REQUIRED_LICENSE_FIELDS = {"identifier", "name", "url"}
REQUIRED_SNAPSHOT_FIELDS = {
    "file",
    "retrieved_on",
    "period_start",
    "period_end",
    "verified_on",
    "raw_sha256",
}


class SourceMetadataError(ValueError):
    """Raised when source metadata is missing, invalid or inconsistent."""


def load_source_metadata(
    metadata_path: str | Path = SOURCE_METADATA_PATH,
) -> dict[str, Any]:
    """Load the structured source record and validate required fields."""

    path = Path(metadata_path)
    if not path.is_file():
        raise FileNotFoundError(f"Metadados da fonte não encontrados: {path}")

    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceMetadataError("Os metadados da fonte não são JSON válido.") from exc

    missing_fields = REQUIRED_METADATA_FIELDS.difference(metadata)
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise SourceMetadataError(f"Campos de proveniência ausentes: {missing}")

    license_record = metadata["license"]
    if not isinstance(license_record, dict):
        raise SourceMetadataError("O registro de licença deve ser um objeto JSON.")

    missing_license_fields = REQUIRED_LICENSE_FIELDS.difference(license_record)
    if missing_license_fields:
        missing = ", ".join(sorted(missing_license_fields))
        raise SourceMetadataError(f"Campos de licença ausentes: {missing}")

    snapshot = metadata["snapshot"]
    if not isinstance(snapshot, dict):
        raise SourceMetadataError("O registro do snapshot deve ser um objeto JSON.")

    missing_snapshot_fields = REQUIRED_SNAPSHOT_FIELDS.difference(snapshot)
    if missing_snapshot_fields:
        missing = ", ".join(sorted(missing_snapshot_fields))
        raise SourceMetadataError(f"Campos do snapshot ausentes: {missing}")

    raw_hash = str(snapshot["raw_sha256"])
    if not re.fullmatch(r"[0-9a-fA-F]{64}", raw_hash):
        raise SourceMetadataError("O hash SHA-256 do snapshot é inválido.")

    return metadata


def validate_raw_snapshot(
    raw_path: str | Path = RAW_DATA_PATH,
    metadata_path: str | Path = SOURCE_METADATA_PATH,
) -> dict[str, Any]:
    """Confirm that the raw file matches its recorded SHA-256 fingerprint."""

    source_path = Path(raw_path)
    if not source_path.is_file():
        raise FileNotFoundError(f"Dataset bruto não encontrado: {source_path}")

    metadata = load_source_metadata(metadata_path)
    recorded_hash = str(metadata["snapshot"]["raw_sha256"]).lower()
    actual_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()

    if actual_hash != recorded_hash:
        raise SourceMetadataError(
            "O snapshot bruto não corresponde ao hash registrado na proveniência."
        )

    return metadata
