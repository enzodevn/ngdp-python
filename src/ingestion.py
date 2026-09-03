"""Safe ingestion of the official Statistics Norway electricity snapshot."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

try:
    from .config import PROCESSED_DATA_PATH, RAW_DATA_PATH, SOURCE_METADATA_PATH
    from .data_cleaning import clean_energy_data
    from .data_loading import load_energy_data
    from .provenance import load_source_metadata, validate_raw_snapshot
except ImportError:  # Supports direct execution from the src directory.
    from config import PROCESSED_DATA_PATH, RAW_DATA_PATH, SOURCE_METADATA_PATH
    from data_cleaning import clean_energy_data
    from data_loading import load_energy_data
    from provenance import load_source_metadata, validate_raw_snapshot


SOURCE_DIMENSION = "Produk2"
CONTENTS_DIMENSION = "ContentsCode"
TIME_DIMENSION = "Tid"
EXPECTED_CONTENT_CODE = "Kraft"
EXPECTED_SOURCE_CODES = ("1.1", "1.2", "1.3", "1.4")
EXPECTED_DIMENSIONS = [SOURCE_DIMENSION, CONTENTS_DIMENSION, TIME_DIMENSION]

JsonLoader = Callable[[str, Mapping[str, str] | None], dict[str, Any]]


class IngestionError(RuntimeError):
    """Raised when an official response cannot be safely ingested."""


@dataclass(frozen=True)
class UpdateSummary:
    """Difference between the local canonical data and an official snapshot."""

    old_period_end: str
    new_period_end: str
    added_rows: int
    revised_rows: int
    removed_rows: int

    @property
    def changed(self) -> bool:
        """Return whether the official snapshot differs from local data."""

        return bool(self.added_rows or self.revised_rows or self.removed_rows)


@dataclass(frozen=True)
class PreparedUpdate:
    """Validated official snapshot ready to be written atomically."""

    raw_text: str
    processed_text: str
    metadata_text: str
    summary: UpdateSummary


def _download_json(
    url: str,
    params: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Download a JSON object from an official public endpoint."""

    query = urlencode(params, safe="*,") if params else ""
    request_url = f"{url}?{query}" if query else url
    request = Request(
        request_url,
        headers={
            "Accept": "application/json",
            "User-Agent": "NGDP data ingestion",
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise IngestionError(
            "Não foi possível obter uma resposta válida da Statistics Norway."
        ) from exc

    if not isinstance(payload, dict):
        raise IngestionError("A API oficial retornou uma estrutura inesperada.")

    return payload


def _ordered_category_codes(dimension: Mapping[str, Any]) -> list[str]:
    """Return JSON-stat category codes in their declared order."""

    category = dimension.get("category", {})
    index = category.get("index", {})

    if isinstance(index, dict):
        return sorted(index, key=index.get)
    if isinstance(index, list):
        return [str(value) for value in index]

    raise IngestionError("A API oficial retornou categorias sem ordem válida.")


def _validate_table_metadata(
    table: Mapping[str, Any],
    source_metadata: Mapping[str, Any],
) -> None:
    """Validate stable table identity before requesting data."""

    if str(table.get("id")) != str(source_metadata["table_id"]):
        raise IngestionError("A API respondeu com uma tabela diferente da esperada.")
    if table.get("source") != source_metadata["provider"]:
        raise IngestionError(
            "O provedor retornado pela API não corresponde ao contrato."
        )
    if table.get("timeUnit") != "Monthly":
        raise IngestionError("A tabela oficial deixou de usar frequência mensal.")
    if table.get("variableNames") != [
        "production and consumption",
        "contents",
        "month",
    ]:
        raise IngestionError("A estrutura da tabela oficial foi alterada.")


def _parse_official_payload(
    payload: Mapping[str, Any],
) -> tuple[list[str], dict[str, str], list[str], list[int | None]]:
    """Validate JSON-stat dimensions and return ordered snapshot values."""

    if payload.get("version") != "2.0" or payload.get("class") != "dataset":
        raise IngestionError("A API não retornou um dataset JSON-stat 2 válido.")
    if payload.get("source") != "Statistics Norway":
        raise IngestionError("A origem do dataset oficial não pôde ser confirmada.")
    if payload.get("id") != EXPECTED_DIMENSIONS:
        raise IngestionError("As dimensões oficiais não correspondem ao contrato NGDP.")

    dimensions = payload.get("dimension")
    if not isinstance(dimensions, dict):
        raise IngestionError("As dimensões do dataset oficial estão ausentes.")

    source_dimension = dimensions.get(SOURCE_DIMENSION, {})
    contents_dimension = dimensions.get(CONTENTS_DIMENSION, {})
    time_dimension = dimensions.get(TIME_DIMENSION, {})

    source_codes = _ordered_category_codes(source_dimension)
    if tuple(source_codes) != EXPECTED_SOURCE_CODES:
        raise IngestionError("As quatro séries oficiais esperadas foram alteradas.")

    source_labels = source_dimension.get("category", {}).get("label", {})
    if set(source_labels) != set(EXPECTED_SOURCE_CODES):
        raise IngestionError("Os rótulos das séries oficiais estão incompletos.")

    content_codes = _ordered_category_codes(contents_dimension)
    if content_codes != [EXPECTED_CONTENT_CODE]:
        raise IngestionError("A métrica oficial de eletricidade foi alterada.")

    unit = (
        contents_dimension.get("category", {})
        .get("unit", {})
        .get(EXPECTED_CONTENT_CODE, {})
        .get("base")
    )
    if unit != "MWh":
        raise IngestionError("A unidade oficial deixou de ser MWh.")

    periods = _ordered_category_codes(time_dimension)
    if not periods or any(
        re.fullmatch(r"\d{4}M(0[1-9]|1[0-2])", period) is None for period in periods
    ):
        raise IngestionError("A API retornou períodos mensais inválidos.")

    size = payload.get("size")
    expected_size = [len(source_codes), 1, len(periods)]
    if size != expected_size:
        raise IngestionError(
            "O tamanho do dataset oficial não corresponde às dimensões."
        )

    values = payload.get("value")
    if not isinstance(values, list) or len(values) != math.prod(expected_size):
        raise IngestionError("A quantidade de valores oficiais é inconsistente.")

    normalized_values: list[int | None] = []
    for value in values:
        if value is None:
            normalized_values.append(None)
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise IngestionError("A API retornou produção não numérica.")
        if not math.isfinite(value) or value < 0 or not float(value).is_integer():
            raise IngestionError("A API retornou produção inválida para a unidade MWh.")
        normalized_values.append(int(value))

    return source_codes, source_labels, periods, normalized_values


def _quote_csv_text(value: str) -> str:
    return f'"{value.replace(chr(34), chr(34) * 2)}"'


def _render_raw_csv(
    title: str,
    source_codes: list[str],
    source_labels: Mapping[str, str],
    periods: list[str],
    values: list[int | None],
) -> str:
    """Render the API response in the established Statistics Norway CSV shape."""

    lines = [_quote_csv_text(title)]
    header = [_quote_csv_text("production and consumption")]
    header.extend(_quote_csv_text(f"Electricity power {period}") for period in periods)
    lines.append(";".join(header))

    period_count = len(periods)
    for source_index, source_code in enumerate(source_codes):
        row = [_quote_csv_text(f"{source_code} {source_labels[source_code]}")]
        start = source_index * period_count
        row.extend(
            ".." if value is None else str(value)
            for value in values[start : start + period_count]
        )
        lines.append(";".join(row))

    return "\n".join(lines) + "\n"


def _normalize_candidate(raw_text: str) -> tuple[str, pd.DataFrame]:
    """Run the normal cleaning and loading contracts against downloaded data."""

    with tempfile.TemporaryDirectory(prefix="ngdp-ingestion-") as temporary_dir:
        temporary_root = Path(temporary_dir)
        raw_path = temporary_root / "raw.csv"
        processed_path = temporary_root / "processed.csv"
        raw_path.write_text(raw_text, encoding="utf-8", newline="")
        clean_energy_data(raw_path, processed_path, verbose=False)
        normalized = load_energy_data(processed_path)
        processed_text = processed_path.read_text(encoding="utf-8")

    return processed_text, normalized


def compare_datasets(
    current: pd.DataFrame,
    candidate: pd.DataFrame,
) -> UpdateSummary:
    """Count additions, official revisions and removals by source-month key."""

    keys = ["energy_source", "date"]
    merged = current.merge(
        candidate,
        on=keys,
        how="outer",
        suffixes=("_current", "_candidate"),
        indicator=True,
    )
    shared = merged["_merge"].eq("both")
    revised = shared & merged["production_mwh_current"].ne(
        merged["production_mwh_candidate"]
    )

    return UpdateSummary(
        old_period_end=current["date"].max().strftime("%YM%m"),
        new_period_end=candidate["date"].max().strftime("%YM%m"),
        added_rows=int(merged["_merge"].eq("right_only").sum()),
        revised_rows=int(revised.sum()),
        removed_rows=int(merged["_merge"].eq("left_only").sum()),
    )


def prepare_official_update(
    *,
    raw_path: str | Path = RAW_DATA_PATH,
    processed_path: str | Path = PROCESSED_DATA_PATH,
    metadata_path: str | Path = SOURCE_METADATA_PATH,
    json_loader: JsonLoader = _download_json,
    retrieved_at: datetime | None = None,
) -> PreparedUpdate:
    """Download, validate and compare the official snapshot without writing files."""

    validate_raw_snapshot(raw_path, metadata_path)
    source_metadata = load_source_metadata(metadata_path)
    api_url = str(source_metadata["api_url"])

    table = json_loader(api_url, {"lang": "en"})
    _validate_table_metadata(table, source_metadata)

    query = {
        "lang": "en",
        f"valueCodes[{SOURCE_DIMENSION}]": ",".join(EXPECTED_SOURCE_CODES),
        f"valueCodes[{CONTENTS_DIMENSION}]": "*",
        f"valueCodes[{TIME_DIMENSION}]": "*",
        "outputFormat": "json-stat2",
    }
    payload = json_loader(f"{api_url}/data", query)
    source_codes, source_labels, periods, values = _parse_official_payload(payload)

    if table.get("lastPeriod") != periods[-1]:
        raise IngestionError(
            "O período final dos metadados diverge do dataset oficial."
        )

    raw_text = _render_raw_csv(
        str(source_metadata["title"]),
        source_codes,
        source_labels,
        periods,
        values,
    )
    processed_text, candidate = _normalize_candidate(raw_text)
    current = load_energy_data(processed_path)
    summary = compare_datasets(current, candidate)

    collected_at = retrieved_at or datetime.now(UTC)
    if collected_at.tzinfo is None:
        collected_at = collected_at.replace(tzinfo=UTC)
    collected_at = collected_at.astimezone(UTC)

    updated_metadata = deepcopy(source_metadata)
    previous_hash = str(source_metadata["snapshot"]["raw_sha256"])
    new_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    updated_metadata["snapshot"].update(
        {
            "retrieved_on": collected_at.isoformat().replace("+00:00", "Z"),
            "retrieval_note": (
                "Retrieved by the NGDP ingestion pipeline from the official "
                "PxWebApi v2 endpoint."
            ),
            "period_start": periods[0],
            "period_end": periods[-1],
            "verified_on": collected_at.date().isoformat(),
            "source_table_period_end_on_verification": periods[-1],
            "source_updated_at": table.get("updated"),
            "record_count": len(candidate),
            "raw_sha256": new_hash,
            "previous_raw_sha256": previous_hash,
            "changes": asdict(summary),
        }
    )
    metadata_text = (
        json.dumps(
            updated_metadata,
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )

    return PreparedUpdate(
        raw_text=raw_text,
        processed_text=processed_text,
        metadata_text=metadata_text,
        summary=summary,
    )


def _atomic_write(path: Path, content: bytes) -> None:
    """Replace one file with a fully written temporary file in the same directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
            temporary_path = Path(temporary_file.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def apply_official_update(
    update: PreparedUpdate,
    *,
    raw_path: str | Path = RAW_DATA_PATH,
    processed_path: str | Path = PROCESSED_DATA_PATH,
    metadata_path: str | Path = SOURCE_METADATA_PATH,
    allow_removals: bool = False,
) -> UpdateSummary:
    """Persist a prepared update, rolling back recoverable write failures."""

    if update.summary.removed_rows and not allow_removals:
        raise IngestionError(
            "A atualização removeria observações existentes e exige revisão manual."
        )
    if not update.summary.changed:
        return update.summary

    contents = {
        Path(raw_path): update.raw_text.encode("utf-8"),
        Path(processed_path): update.processed_text.encode("utf-8"),
        Path(metadata_path): update.metadata_text.encode("utf-8"),
    }
    original_contents = {
        path: path.read_bytes() if path.exists() else None for path in contents
    }

    try:
        for path, content in contents.items():
            _atomic_write(path, content)
        validate_raw_snapshot(raw_path, metadata_path)
        load_energy_data(processed_path)
    except (OSError, ValueError) as exc:
        for path, original in original_contents.items():
            if original is not None:
                _atomic_write(path, original)
            elif path.exists():
                path.unlink()
        raise IngestionError(
            "A atualização falhou e os arquivos foram restaurados."
        ) from exc

    return update.summary
