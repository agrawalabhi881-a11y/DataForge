
"""
DataForge 
Module: JSON and JSONL Dataset Loader

Loads JSON and JSONL cybersecurity datasets into Pandas
DataFrames and extracts metadata without modifying raw files.
"""

import json
from pathlib import Path
from typing import Iterator

import pandas as pd


SUPPORTED_FORMATS = {".json", ".jsonl"}


def validate_json_file(file_path: str | Path) -> Path:
    """Validate the existence and extension of a JSON file."""

    path = Path(file_path).expanduser()

    if not path.is_file():
        raise FileNotFoundError(
            f"Dataset file does not exist: {path}"
        )

    if path.suffix.lower() not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported file format: {path.suffix}. "
            "Expected .json or .jsonl."
        )

    return path


def _validate_records(records: object) -> list[dict]:
    """
    Ensure that dataset records are a list of JSON objects.

    This prevents unexpected structures from being silently
    interpreted as tabular records.
    """

    if not isinstance(records, list):
        raise ValueError(
            "Dataset records must be a list of JSON objects."
        )

    if not all(isinstance(record, dict) for record in records):
        raise ValueError(
            "Every dataset record must be a JSON object."
        )

    return records


def _extract_json_records(data: object) -> list[dict]:
    """
    Accept a JSON array or a supported object wrapper.

    Supported forms:
    1. [{...}, {...}]
    2. {"records": [{...}, {...}]}
    3. {"data": [{...}, {...}]}
    """

    if isinstance(data, list):
        return _validate_records(data)

    if isinstance(data, dict):
        for key in ("records", "data"):
            if key in data:
                return _validate_records(data[key])

    raise ValueError(
        "Unsupported JSON dataset structure. "
        "Expected an array of objects or an object "
        "containing a 'records' or 'data' array."
    )


def load_json(
    file_path: str | Path,
    encoding: str = "utf-8-sig",
) -> pd.DataFrame:
    """
    Load JSON or JSONL records into a Pandas DataFrame.

    JSON files are parsed as complete documents.
    JSONL files are parsed one line at a time.
    """

    path = validate_json_file(file_path)

    if path.suffix.lower() == ".jsonl":
        records = []

        with path.open("r", encoding=encoding) as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(
                        f"Invalid JSONL at line {line_number}: "
                        f"{error.msg}"
                    ) from error

                if not isinstance(record, dict):
                    raise ValueError(
                        f"JSONL line {line_number} must "
                        "contain a JSON object."
                    )

                records.append(record)

    else:
        try:
            with path.open("r", encoding=encoding) as file:
                data = json.load(file)

        except json.JSONDecodeError as error:
            raise ValueError(
                f"Invalid JSON file: {path}. {error.msg}"
            ) from error

        records = _extract_json_records(data)

    return pd.DataFrame.from_records(records)


def load_jsonl_in_chunks(
    file_path: str | Path,
    chunk_size: int = 10000,
    encoding: str = "utf-8-sig",
) -> Iterator[pd.DataFrame]:
    """
    Stream a JSONL dataset in smaller DataFrame batches.

    The complete dataset is not loaded into memory.
    """

    path = validate_json_file(file_path)

    if path.suffix.lower() != ".jsonl":
        raise ValueError(
            "Chunk loading is supported only for JSONL files."
        )

    if (
        not isinstance(chunk_size, int)
        or isinstance(chunk_size, bool)
        or chunk_size <= 0
    ):
        raise ValueError(
            "chunk_size must be a positive integer."
        )

    records = []

    with path.open("r", encoding=encoding) as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSONL at line {line_number}: "
                    f"{error.msg}"
                ) from error

            if not isinstance(record, dict):
                raise ValueError(
                    f"JSONL line {line_number} must "
                    "contain a JSON object."
                )

            records.append(record)

            if len(records) == chunk_size:
                yield pd.DataFrame.from_records(records)
                records = []

    if records:
        yield pd.DataFrame.from_records(records)


def extract_json_metadata(
    dataframe: pd.DataFrame,
    file_path: str | Path,
) -> dict:
    """
    Extract metadata from a loaded JSON or JSONL dataset.
    """

    path = validate_json_file(file_path)

    metadata = {
        "file_name": path.name,
        "file_format": path.suffix.lower().lstrip("."),
        "file_size_bytes": path.stat().st_size,
        "record_count": int(len(dataframe)),
        "column_count": int(len(dataframe.columns)),
        "columns": dataframe.columns.tolist(),
        "data_types": {
            column: str(dtype)
            for column, dtype in dataframe.dtypes.items()
        },
        "missing_values": {
            column: int(count)
            for column, count
            in dataframe.isna().sum().items()
        },
    }

    return metadata
