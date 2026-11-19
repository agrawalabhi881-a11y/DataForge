
"""
DataForge
Module: Excel Dataset Loader

Load Excel datasets, select worksheets, extract metadata,
and process worksheet rows in batches.

Supported formats: .xlsx and .xlsm
"""

from pathlib import Path
from typing import Iterator

import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException


SUPPORTED_FORMATS = {".xlsx", ".xlsm"}


def validate_excel_file(file_path: str | Path) -> Path:
    """Check that the Excel file exists and is supported."""

    path = Path(file_path).expanduser()

    if not path.is_file():
        raise FileNotFoundError(
            f"Excel file does not exist: {path}"
        )

    if path.suffix.lower() not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported Excel format: {path.suffix}. "
            "Expected .xlsx or .xlsm."
        )

    return path


def _open_workbook(file_path: str | Path):
    """Open an Excel workbook in read-only mode."""

    path = validate_excel_file(file_path)

    try:
        return load_workbook(
            filename=path,
            read_only=True,
            data_only=True,
            keep_links=False,
        )
    except (OSError, ValueError, InvalidFileException) as error:
        raise ValueError(
            f"Unable to open Excel workbook: {path}"
        ) from error


def _select_worksheet(workbook, sheet_name: str | int):
    """Select a worksheet by name or zero-based index."""

    if isinstance(sheet_name, bool):
        raise TypeError(
            "sheet_name must be a string or integer."
        )

    if isinstance(sheet_name, int):
        if not 0 <= sheet_name < len(workbook.worksheets):
            raise ValueError(
                f"Worksheet index out of range: {sheet_name}"
            )
        return workbook.worksheets[sheet_name]

    if isinstance(sheet_name, str):
        if sheet_name not in workbook.sheetnames:
            raise ValueError(
                f"Worksheet not found: {sheet_name}. "
                f"Available sheets: {workbook.sheetnames}"
            )
        return workbook[sheet_name]

    raise TypeError(
        "sheet_name must be a string or integer."
    )


def load_excel(
    file_path: str | Path,
    sheet_name: str | int | None = 0,
    usecols: str | list[str] | None = None,
) -> pd.DataFrame | dict[str, pd.DataFrame]:
    """
    Load one or all worksheets into Pandas DataFrames.

    sheet_name=None loads every worksheet.
    usecols follows pandas.read_excel() conventions.
    """

    path = validate_excel_file(file_path)

    workbook = _open_workbook(path)

    try:
        if sheet_name is not None:
            _select_worksheet(workbook, sheet_name)

        try:
            result = pd.read_excel(
                path,
                sheet_name=sheet_name,
                usecols=usecols,
                engine="openpyxl",
            )
        except (
            OSError,
            ValueError,
            TypeError,
            InvalidFileException,
        ) as error:
            raise ValueError(
                f"Unable to load Excel dataset: {path}. "
                f"{error}"
            ) from error

        return result

    finally:
        workbook.close()


def load_excel_in_batches(
    file_path: str | Path,
    sheet_name: str | int = 0,
    batch_size: int = 10000,
) -> Iterator[pd.DataFrame]:
    """
    Stream Excel worksheet rows in DataFrame batches.

    The first row is treated as the column header.
    Subsequent rows are returned in batches.
    """

    if (
        not isinstance(batch_size, int)
        or isinstance(batch_size, bool)
        or batch_size <= 0
    ):
        raise ValueError(
            "batch_size must be a positive integer."
        )

    workbook = _open_workbook(file_path)

    try:
        worksheet = _select_worksheet(
            workbook, sheet_name
        )

        rows = worksheet.iter_rows(values_only=True)

        header = next(rows, None)

        if header is None:
            return

        columns = [
            str(value) if value is not None
            else f"Unnamed: {index}"
            for index, value in enumerate(header)
        ]

        batch = []

        for row in rows:
            batch.append(row)

            if len(batch) == batch_size:
                yield pd.DataFrame(
                    batch,
                    columns=columns,
                )
                batch = []

        if batch:
            yield pd.DataFrame(
                batch,
                columns=columns,
            )

    finally:
        workbook.close()


def extract_excel_metadata(
    dataframe: pd.DataFrame,
    file_path: str | Path,
    sheet_name: str | int = 0,
) -> dict:
    """
    Extract metadata from a loaded Excel worksheet.
    """

    path = validate_excel_file(file_path)
    workbook = _open_workbook(path)

    try:
        worksheet = _select_worksheet(
            workbook, sheet_name
        )

        metadata = {
            "file_name": path.name,
            "file_format": path.suffix.lower().lstrip("."),
            "file_size_bytes": path.stat().st_size,
            "sheet_name": worksheet.title,
            "available_sheets": workbook.sheetnames,
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

    finally:
        workbook.close()
