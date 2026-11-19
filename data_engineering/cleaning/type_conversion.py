
"""
DataForge - Data Engineering
Module: Data Type Conversion

Convert dataset columns to specified data types while
preserving original data and tracking transformations.
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd


SUPPORTED_TYPES = {
    "integer",
    "float",
    "string",
    "boolean",
    "datetime",
}

TRUE_VALUES = {"true", "1", "yes", "y", "t"}
FALSE_VALUES = {"false", "0", "no", "n", "f"}


@dataclass
class TypeConversionResult:
    """Store converted data and transformation details."""

    dataframe: pd.DataFrame
    transformations: list[dict[str, Any]]


def validate_conversion_mapping(
    dataframe: pd.DataFrame,
    column_types: dict[str, str],
) -> None:
    """Validate requested column type conversions."""

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a Pandas DataFrame.")

    if not dataframe.columns.is_unique:
        raise ValueError("DataFrame column names must be unique.")

    if not isinstance(column_types, dict):
        raise TypeError("column_types must be a dictionary.")

    for column, target_type in column_types.items():
        if not isinstance(column, str):
            raise TypeError("Column names must be strings.")

        if column not in dataframe.columns:
            raise ValueError(
                f"Column not found: {column}"
            )

        if target_type not in SUPPORTED_TYPES:
            raise ValueError(
                f"Unsupported target type for '{column}': "
                f"{target_type}"
            )


def _convert_boolean(series: pd.Series) -> pd.Series:
    """Convert recognized boolean representations."""

    def parse_boolean(value):
        if pd.isna(value):
            return pd.NA

        if isinstance(value, bool):
            return value

        normalized = str(value).strip().lower()

        if normalized in TRUE_VALUES:
            return True

        if normalized in FALSE_VALUES:
            return False

        raise ValueError(
            f"Unrecognized boolean value: {value}"
        )

    return series.map(parse_boolean).astype("boolean")


def _convert_integer(series: pd.Series) -> pd.Series:
    """Convert numeric values to nullable integers."""

    numeric = pd.to_numeric(series, errors="raise")

    valid = numeric.dropna()

    if not valid.empty:
        if not (valid % 1 == 0).all():
            raise ValueError(
                "Cannot convert fractional values to integers."
            )

    return numeric.astype("Int64")


def _convert_series(
    series: pd.Series,
    target_type: str,
    datetime_format: str | None = None,
) -> pd.Series:
    """Apply a supported data type conversion."""

    if target_type == "integer":
        return _convert_integer(series)

    if target_type == "float":
        return pd.to_numeric(
            series, errors="raise"
        ).astype("Float64")

    if target_type == "string":
        return series.astype("string")

    if target_type == "boolean":
        return _convert_boolean(series)

    if target_type == "datetime":
        return pd.to_datetime(
            series,
            format=datetime_format,
            errors="raise",
        )

    raise ValueError(
        f"Unsupported target type: {target_type}"
    )


def convert_column_type(
    dataframe: pd.DataFrame,
    column: str,
    target_type: str,
    datetime_format: str | None = None,
) -> TypeConversionResult:
    """Convert a single DataFrame column."""

    formats = (
        {column: datetime_format}
        if datetime_format is not None else None
    )

    return convert_data_types(
        dataframe,
        column_types={column: target_type},
        datetime_formats=formats,
    )


def convert_data_types(
    dataframe: pd.DataFrame,
    column_types: dict[str, str],
    datetime_formats: dict[str, str] | None = None,
) -> TypeConversionResult:
    """
    Convert multiple columns according to a type mapping.

    All conversions are applied to a copy. If any
    conversion fails, no partially converted result
    is returned.
    """

    validate_conversion_mapping(
        dataframe, column_types
    )

    if datetime_formats is None:
        datetime_formats = {}

    if not isinstance(datetime_formats, dict):
        raise TypeError(
            "datetime_formats must be a dictionary."
        )

    for column, date_format in datetime_formats.items():
        if column not in column_types:
            raise ValueError(
                f"Datetime format specified for "
                f"unmapped column: {column}"
            )

        if column_types[column] != "datetime":
            raise ValueError(
                f"Column '{column}' must target datetime "
                "to use a datetime format."
            )

        if not isinstance(date_format, str):
            raise TypeError(
                "Datetime formats must be strings."
            )

    converted = dataframe.copy(deep=True)
    transformations = []

    for column, target_type in column_types.items():
        original_dtype = str(converted[column].dtype)
        missing_before = int(
            converted[column].isna().sum()
        )

        try:
            converted[column] = _convert_series(
                converted[column],
                target_type,
                datetime_format=datetime_formats.get(
                    column
                ),
            )

        except (ValueError, TypeError, OverflowError) as error:
            raise ValueError(
                f"Failed to convert column '{column}' "
                f"to {target_type}: {error}"
            ) from error

        transformations.append({
            "operation": "type_conversion",
            "column": column,
            "target_type": target_type,
            "dtype_before": original_dtype,
            "dtype_after": str(
                converted[column].dtype
            ),
            "missing_before": missing_before,
            "missing_after": int(
                converted[column].isna().sum()
            ),
        })

    return TypeConversionResult(
        dataframe=converted,
        transformations=transformations,
    )
