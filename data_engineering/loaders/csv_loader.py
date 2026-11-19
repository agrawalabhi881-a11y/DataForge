
"""
DataForge 
Module: CSV Dataset Loader

Loads CSV datasets and extracts basic metadata.
Original source files are never modified.
"""

from pathlib import Path
from typing import Iterator

import pandas as pd


def validate_csv_file(file_path: str | Path) -> Path:
    """Validate the location and extension of a CSV file."""

    path = Path(file_path).expanduser()

    if not path.is_file():
        raise FileNotFoundError(
            f"CSV file does not exist: {path}"
        )

    if path.suffix.lower() != ".csv":
        raise ValueError(
            f"Unsupported file format: {path.suffix}. "
            "Expected a .csv file."
        )

    return path


def load_csv(
    file_path: str | Path,
    encoding: str = "utf-8",
    **kwargs,
) -> pd.DataFrame:
    """
    Load a CSV dataset into a Pandas DataFrame.

    Additional keyword arguments are passed to
    pandas.read_csv().
    """

    path = validate_csv_file(file_path)

    try:
        dataframe = pd.read_csv(
            path,
            encoding=encoding,
            **kwargs,
        )

    except (pd.errors.ParserError, UnicodeError) as error:
        raise ValueError(
            f"Unable to parse CSV file: {path}"
        ) from error

    return dataframe


def load_csv_in_chunks(
    file_path: str | Path,
    chunk_size: int = 10000,
    encoding: str = "utf-8",
    **kwargs,
) -> Iterator[pd.DataFrame]:
    """
    Read a large CSV dataset in smaller batches.

    Each batch is returned as a Pandas DataFrame.
    """

    path = validate_csv_file(file_path)

    if not isinstance(chunk_size, int) or isinstance(
        chunk_size, bool
    ) or chunk_size <= 0:
        raise ValueError(
            "chunk_size must be a positive integer."
        )

    if "chunksize" in kwargs or "iterator" in kwargs:
        raise ValueError(
            "Use chunk_size instead of chunksize or iterator."
        )

    reader = pd.read_csv(
        path,
        chunksize=chunk_size,
        encoding=encoding,
        **kwargs,
    )

    yield from reader


def extract_csv_metadata(
    dataframe: pd.DataFrame,
    file_path: str | Path,
) -> dict:
    """
    Extract basic metadata from a loaded CSV dataset.
    """

    path = validate_csv_file(file_path)

    metadata = {
        "file_name": path.name,
        "file_format": "csv",
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
