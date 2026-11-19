
"""
DataForge - Data Engineering
Module: Schema Transformation

Apply explicitly supplied schema mappings and type
requirements without modifying source datasets.
"""

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from data_engineering.cleaning.type_conversion import (
    convert_data_types,
)


SUPPORTED_TYPES = {
    "integer",
    "float",
    "string",
    "boolean",
    "datetime",
}


@dataclass
class SchemaTransformationResult:
    dataframe: pd.DataFrame
    schema_version: str
    transformations: list[dict[str, Any]]
    warnings: list[str] = field(default_factory=list)


def _validate_schema(
    dataframe: pd.DataFrame,
    column_mapping: dict[str, str],
    column_types: dict[str, str] | None,
    required_columns: list[str] | None,
    schema_version: str,
) -> None:
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a Pandas DataFrame.")

    if not dataframe.columns.is_unique:
        raise ValueError("Source column names must be unique.")

    if not isinstance(column_mapping, dict):
        raise TypeError("column_mapping must be a dictionary.")

    if not all(
        isinstance(source, str)
        and isinstance(target, str)
        and source
        and target
        for source, target in column_mapping.items()
    ):
        raise ValueError(
            "Column mappings must contain non-empty string names."
        )

    missing_sources = [
        source for source in column_mapping
        if source not in dataframe.columns
    ]

    if missing_sources:
        raise ValueError(
            f"Source columns not found: {missing_sources}"
        )

    if len(set(column_mapping.values())) != len(column_mapping):
        raise ValueError(
            "Multiple source columns cannot map to the same target."
        )

    final_columns = [
        column_mapping.get(column, column)
        for column in dataframe.columns
    ]

    if len(set(final_columns)) != len(final_columns):
        raise ValueError(
            "Column mapping creates duplicate output names."
        )

    if column_types is not None:
        if not isinstance(column_types, dict):
            raise TypeError("column_types must be a dictionary.")

        for column, target_type in column_types.items():
            if column not in final_columns:
                raise ValueError(
                    f"Type mapping references unknown column: {column}"
                )

            if target_type not in SUPPORTED_TYPES:
                raise ValueError(
                    f"Unsupported target type: {target_type}"
                )

    if required_columns is not None:
        if (
            not isinstance(required_columns, list)
            or not all(
                isinstance(column, str) and column
                for column in required_columns
            )
        ):
            raise TypeError(
                "required_columns must be a list of non-empty strings."
            )

        if len(set(required_columns)) != len(required_columns):
            raise ValueError(
                "Duplicate required columns are not allowed."
            )

    if not isinstance(schema_version, str) or not schema_version.strip():
        raise ValueError("schema_version must be a non-empty string.")


def transform_schema(
    dataframe: pd.DataFrame,
    column_mapping: dict[str, str],
    column_types: dict[str, str] | None = None,
    required_columns: list[str] | None = None,
    schema_version: str = "1.0",
    add_missing_columns: bool = False,
    drop_unmapped_columns: bool = False,
    datetime_formats: dict[str, str] | None = None,
) -> SchemaTransformationResult:
    """
    Transform a dataset using an explicit schema configuration.

    Source column names are keys in column_mapping.
    Canonical column names are the corresponding values.
    """

    _validate_schema(
        dataframe,
        column_mapping,
        column_types,
        required_columns,
        schema_version,
    )

    if not isinstance(add_missing_columns, bool):
        raise TypeError("add_missing_columns must be a boolean.")

    if not isinstance(drop_unmapped_columns, bool):
        raise TypeError("drop_unmapped_columns must be a boolean.")

    result = dataframe.copy(deep=True)
    transformations = []
    warnings = []

    if drop_unmapped_columns:
        unmapped = [
            column for column in result.columns
            if column not in column_mapping
        ]

        result = result.drop(columns=unmapped)

        transformations.append({
            "operation": "drop_unmapped_columns",
            "columns": unmapped,
        })

    result = result.rename(columns=column_mapping)

    transformations.append({
        "operation": "column_mapping",
        "mapping": column_mapping.copy(),
    })

    required = required_columns or []

    missing_required = [
        column for column in required
        if column not in result.columns
    ]

    if missing_required:
        if not add_missing_columns:
            raise ValueError(
                f"Missing required columns: {missing_required}"
            )

        for column in missing_required:
            result[column] = pd.NA

        warnings.append(
            "Required columns added with missing values: "
            + ", ".join(missing_required)
        )

        transformations.append({
            "operation": "add_missing_columns",
            "columns": missing_required,
        })

    if column_types:
        converted = convert_data_types(
            result,
            column_types=column_types,
            datetime_formats=datetime_formats,
        )

        result = converted.dataframe
        transformations.extend(converted.transformations)

    elif datetime_formats:
        raise ValueError(
            "datetime_formats requires column_types."
        )

    transformations.append({
        "operation": "schema_version_tracking",
        "schema_version": schema_version,
    })

    return SchemaTransformationResult(
        dataframe=result,
        schema_version=schema_version,
        transformations=transformations,
        warnings=warnings,
    )
