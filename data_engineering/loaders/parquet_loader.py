
"""
DataForge 
Module: Parquet Dataset Loader

Load Parquet datasets, extract metadata, and stream
large datasets in batches without modifying raw files.
"""

from pathlib import Path
from typing import Iterator

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def validate_parquet_file(file_path: str | Path) -> Path:
    """
    Validate that the supplied path points to an existing
    Parquet file.
    """

    path = Path(file_path).expanduser()

    if not path.is_file():
        raise FileNotFoundError(
            f"Parquet file does not exist: {path}"
        )

    if path.suffix.lower() != ".parquet":
        raise ValueError(
            f"Unsupported file format: {path.suffix}. "
            "Expected a .parquet file."
        )

    return path


def _open_parquet_file(file_path: str | Path) -> pq.ParquetFile:
    """
    Open and validate the internal Parquet structure.
    """

    path = validate_parquet_file(file_path)

    try:
        return pq.ParquetFile(path)

    except (pa.ArrowException, OSError, ValueError) as error:
        raise ValueError(
            f"Unable to read Parquet file: {path}"
        ) from error


def _validate_columns(
    parquet_file: pq.ParquetFile,
    columns: list[str] | None,
) -> list[str] | None:
    """
    Validate requested columns against the Parquet schema.
    """

    if columns is None:
        return None

    if not isinstance(columns, list) or any(
        not isinstance(column, str) for column in columns
    ):
        raise TypeError(
            "columns must be a list of column names or None."
        )

    available_columns = parquet_file.schema_arrow.names

    missing_columns = [
        column
        for column in columns
        if column not in available_columns
    ]

    if missing_columns:
        raise ValueError(
            f"Columns not found in Parquet file: "
            f"{missing_columns}"
        )

    return columns


def load_parquet(
    file_path: str | Path,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    Load a Parquet dataset into a Pandas DataFrame.

    Optionally load only selected columns.
    """

    parquet_file = _open_parquet_file(file_path)

    selected_columns = _validate_columns(
        parquet_file,
        columns,
    )

    try:
        table = parquet_file.read(
            columns=selected_columns
        )

        return table.to_pandas()

    except (pa.ArrowException, OSError, ValueError) as error:
        raise ValueError(
            f"Failed to load Parquet dataset: {file_path}"
        ) from error


def load_parquet_in_batches(
    file_path: str | Path,
    batch_size: int = 10000,
    columns: list[str] | None = None,
) -> Iterator[pd.DataFrame]:
    """
    Stream Parquet data as smaller Pandas DataFrames.

    Only the current batch is converted into a DataFrame.
    """

    if (
        not isinstance(batch_size, int)
        or isinstance(batch_size, bool)
        or batch_size <= 0
    ):
        raise ValueError(
            "batch_size must be a positive integer."
        )

    parquet_file = _open_parquet_file(file_path)

    selected_columns = _validate_columns(
        parquet_file,
        columns,
    )

    try:
        for batch in parquet_file.iter_batches(
            batch_size=batch_size,
            columns=selected_columns,
        ):
            yield batch.to_pandas()

    except (pa.ArrowException, OSError, ValueError) as error:
        raise ValueError(
            f"Failed to stream Parquet dataset: {file_path}"
        ) from error


def extract_parquet_metadata(
    file_path: str | Path,
    dataframe: pd.DataFrame | None = None,
) -> dict:
    """
    Extract file-level metadata from a Parquet dataset.

    File-level record counts and schema are obtained
    directly from the Parquet metadata.

    Missing-value counts are calculated only when a
    DataFrame is supplied.
    """

    path = validate_parquet_file(file_path)
    parquet_file = _open_parquet_file(path)

    file_metadata = parquet_file.metadata
    schema = parquet_file.schema_arrow

    metadata = {
        "file_name": path.name,
        "file_format": "parquet",
        "file_size_bytes": path.stat().st_size,
        "record_count": int(file_metadata.num_rows),
        "column_count": len(schema.names),
        "columns": schema.names,
        "data_types": {
            field.name: str(field.type)
            for field in schema
        },
        "row_group_count": int(
            file_metadata.num_row_groups
        ),
        "missing_values": None,
    }

    if dataframe is not None:
        metadata["missing_values"] = {
            column: int(count)
            for column, count
            in dataframe.isna().sum().items()
        }

    return metadata
