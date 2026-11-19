
"""
DataForge - Data Engineering
Module: Unified Dataset Loader

Provide a common interface for loading supported
datasets and extracting standardized metadata.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pandas as pd

from data_engineering.loaders.csv_loader import (
    load_csv,
    load_csv_in_chunks,
    extract_csv_metadata,
)
from data_engineering.loaders.json_loader import (
    load_json,
    load_jsonl_in_chunks,
    extract_json_metadata,
)
from data_engineering.loaders.parquet_loader import (
    load_parquet,
    load_parquet_in_batches,
    extract_parquet_metadata,
)
from data_engineering.loaders.excel_loader import (
    load_excel,
    load_excel_in_batches,
    extract_excel_metadata,
)
from data_engineering.loaders.zip_loader import (
    load_zip_dataset,
    extract_zip_metadata,
)


SUPPORTED_FORMATS = {
    ".csv",
    ".json",
    ".jsonl",
    ".parquet",
    ".xlsx",
    ".xlsm",
    ".zip",
}

BATCH_FORMATS = {
    ".csv",
    ".jsonl",
    ".parquet",
    ".xlsx",
    ".xlsm",
}


@dataclass
class DatasetResult:
    """Store a loaded dataset and its metadata."""

    dataframe: pd.DataFrame
    metadata: dict


def detect_file_format(file_path: str | Path) -> str:
    """Identify the dataset format from its extension."""

    path = Path(file_path).expanduser()
    extension = path.suffix.lower()

    if extension not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported dataset format: {extension}. "
            f"Supported formats: {sorted(SUPPORTED_FORMATS)}"
        )

    return extension


def _standardize_metadata(
    metadata: dict,
    file_path: str | Path,
    dataframe: pd.DataFrame,
) -> dict:
    """Return consistent metadata across dataset formats."""

    path = Path(file_path).expanduser()

    return {
        "file_name": metadata.get("file_name", path.name),
        "file_format": metadata.get(
            "file_format", path.suffix.lower().lstrip(".")
        ),
        "file_size_bytes": metadata.get(
            "file_size_bytes", path.stat().st_size
        ),
        "record_count": int(len(dataframe)),
        "column_count": int(len(dataframe.columns)),
        "columns": dataframe.columns.tolist(),
        "data_types": {
            str(column): str(dtype)
            for column, dtype in dataframe.dtypes.items()
        },
        "missing_values": {
            str(column): int(count)
            for column, count
            in dataframe.isna().sum().items()
        },
        "source_metadata": metadata,
    }


def load_dataset(
    file_path: str | Path,
    *,
    sheet_name: str | int = 0,
    member_name: str | None = None,
    columns: list[str] | None = None,
) -> DatasetResult:
    """
    Load a supported dataset and return standardized metadata.

    Excel loading supports one worksheet per call.
    ZIP loading supports one archive member per call.
    """

    path = Path(file_path).expanduser()

    if not path.is_file():
        raise FileNotFoundError(
            f"Dataset file does not exist: {path}"
        )

    extension = detect_file_format(path)

    if member_name is not None and extension != ".zip":
        raise ValueError(
            "member_name is supported only for ZIP files."
        )

    if sheet_name != 0 and extension not in {".xlsx", ".xlsm"}:
        raise ValueError(
            "sheet_name is supported only for Excel files."
        )

    if columns is not None and extension not in {
        ".csv", ".parquet", ".xlsx", ".xlsm"
    }:
        raise ValueError(
            "Column selection is not supported for this format."
        )

    if columns is not None and (
        not isinstance(columns, list)
        or not all(isinstance(c, str) for c in columns)
    ):
        raise TypeError(
            "columns must be a list of strings or None."
        )

    if extension == ".csv":
        if columns is None:
            dataframe = load_csv(path)
        else:
            dataframe = load_csv(path, usecols=columns)

        metadata = extract_csv_metadata(dataframe, path)

    elif extension in {".json", ".jsonl"}:
        dataframe = load_json(path)
        metadata = extract_json_metadata(dataframe, path)

    elif extension == ".parquet":
        dataframe = load_parquet(path, columns=columns)
        metadata = extract_parquet_metadata(path, dataframe)

    elif extension in {".xlsx", ".xlsm"}:
        dataframe = load_excel(
            path,
            sheet_name=sheet_name,
            usecols=columns,
        )
        metadata = extract_excel_metadata(
            dataframe,
            path,
            sheet_name=sheet_name,
        )

    elif extension == ".zip":
        dataframe = load_zip_dataset(
            path,
            member_name=member_name,
        )

        if member_name is None:
            from data_engineering.loaders.zip_loader import (
                list_zip_datasets,
            )
            member_name = list_zip_datasets(path)[0]

        metadata = extract_zip_metadata(
            path,
            member_name,
            dataframe,
        )

    else:
        raise ValueError(
            f"Unsupported dataset format: {extension}"
        )

    standardized = _standardize_metadata(
        metadata,
        path,
        dataframe,
    )

    if extension == ".zip":
        standardized["file_format"] = "zip"
        standardized["archive_member_format"] = (
            metadata["file_format"]
        )

    return DatasetResult(
        dataframe=dataframe,
        metadata=standardized,
    )


def load_dataset_in_batches(
    file_path: str | Path,
    *,
    batch_size: int = 10000,
    sheet_name: str | int = 0,
    columns: list[str] | None = None,
) -> Iterator[pd.DataFrame]:
    """
    Stream supported datasets as Pandas DataFrame batches.

    JSON documents and ZIP archives are not streamed
    by this interface.
    """

    if (
        not isinstance(batch_size, int)
        or isinstance(batch_size, bool)
        or batch_size <= 0
    ):
        raise ValueError(
            "batch_size must be a positive integer."
        )

    path = Path(file_path).expanduser()

    if not path.is_file():
        raise FileNotFoundError(
            f"Dataset file does not exist: {path}"
        )

    extension = detect_file_format(path)

    if extension not in BATCH_FORMATS:
        raise ValueError(
            f"Batch loading is not supported for {extension}."
        )

    if sheet_name != 0 and extension not in {".xlsx", ".xlsm"}:
        raise ValueError(
            "sheet_name is supported only for Excel files."
        )

    if columns is not None and extension not in {
        ".csv", ".parquet"
    }:
        raise ValueError(
            "Batch column selection supports CSV and Parquet only."
        )

    if columns is not None and (
        not isinstance(columns, list)
        or not all(isinstance(c, str) for c in columns)
    ):
        raise TypeError(
            "columns must be a list of strings or None."
        )

    if extension == ".csv":
        options = (
            {"usecols": columns}
            if columns is not None else {}
        )
        yield from load_csv_in_chunks(
            path,
            chunk_size=batch_size,
            **options,
        )

    elif extension == ".jsonl":
        yield from load_jsonl_in_chunks(
            path,
            chunk_size=batch_size,
        )

    elif extension == ".parquet":
        yield from load_parquet_in_batches(
            path,
            batch_size=batch_size,
            columns=columns,
        )

    elif extension in {".xlsx", ".xlsm"}:
        yield from load_excel_in_batches(
            path,
            sheet_name=sheet_name,
            batch_size=batch_size,
        )
