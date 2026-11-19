
"""
DataForge - Data Engineering
Module: String Normalization

Normalize text and categorical fields while preserving
original data and recording applied transformations.
"""

from dataclasses import dataclass
from typing import Any
import unicodedata

import pandas as pd


SUPPORTED_OPERATIONS = {
    "strip",
    "collapse_whitespace",
    "lowercase",
    "uppercase",
    "casefold",
    "unicode",
}


@dataclass
class StringNormalizationResult:
    dataframe: pd.DataFrame
    transformations: list[dict[str, Any]]
    statistics: pd.DataFrame


def _validate_dataframe(dataframe: pd.DataFrame) -> None:
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a Pandas DataFrame.")

    if not dataframe.columns.is_unique:
        raise ValueError("DataFrame column names must be unique.")


def _validate_columns(
    dataframe: pd.DataFrame,
    columns: list[str] | None,
) -> list[str]:
    if columns is None:
        return dataframe.select_dtypes(
            include=["object", "string"]
        ).columns.tolist()

    if (
        not isinstance(columns, list)
        or not columns
        or not all(isinstance(c, str) for c in columns)
    ):
        raise TypeError("columns must be a non-empty list of strings.")

    if len(columns) != len(set(columns)):
        raise ValueError("Duplicate column names are not allowed.")

    missing = [c for c in columns if c not in dataframe.columns]

    if missing:
        raise ValueError(f"Columns not found: {missing}")

    return columns


def _normalize_value(
    value: Any,
    operations: list[str],
    unicode_form: str,
) -> Any:
    if not isinstance(value, str):
        return value

    normalized = value

    for operation in operations:
        if operation == "strip":
            normalized = normalized.strip()

        elif operation == "collapse_whitespace":
            normalized = " ".join(normalized.split())

        elif operation == "lowercase":
            normalized = normalized.lower()

        elif operation == "uppercase":
            normalized = normalized.upper()

        elif operation == "casefold":
            normalized = normalized.casefold()

        elif operation == "unicode":
            normalized = unicodedata.normalize(
                unicode_form, normalized
            )

    return normalized


def analyze_string_columns(
    dataframe: pd.DataFrame,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Calculate basic statistics for text columns."""

    _validate_dataframe(dataframe)
    selected = _validate_columns(dataframe, columns)

    records = []

    for column in selected:
        series = dataframe[column]
        text_values = series.dropna()
        text_values = text_values[
            text_values.map(lambda value: isinstance(value, str))
        ]

        records.append({
            "column": column,
            "total_records": len(series),
            "missing_values": int(series.isna().sum()),
            "string_values": len(text_values),
            "leading_or_trailing_whitespace": int(
                text_values.map(
                    lambda value: value != value.strip()
                ).sum()
            ),
            "empty_strings": int(
                text_values.map(
                    lambda value: value.strip() == ""
                ).sum()
            ),
            "unique_values": int(series.nunique(dropna=True)),
        })

    return pd.DataFrame(records)


def normalize_strings(
    dataframe: pd.DataFrame,
    columns: list[str] | None = None,
    operations: list[str] | None = None,
    unicode_form: str = "NFC",
) -> StringNormalizationResult:
    """
    Normalize selected text columns using explicit operations.

    No case conversion is applied by default because case
    may be meaningful in URLs, paths, code, and security logs.
    """

    _validate_dataframe(dataframe)
    selected = _validate_columns(dataframe, columns)

    if operations is None:
        operations = ["strip"]

    if not isinstance(operations, list) or not operations:
        raise ValueError("operations must be a non-empty list.")

    if not all(isinstance(op, str) for op in operations):
        raise TypeError("All operations must be strings.")

    unsupported = [
        op for op in operations
        if op not in SUPPORTED_OPERATIONS
    ]

    if unsupported:
        raise ValueError(
            f"Unsupported operations: {unsupported}"
        )

    if unicode_form not in {"NFC", "NFD", "NFKC", "NFKD"}:
        raise ValueError("Invalid Unicode normalization form.")

    result = dataframe.copy(deep=True)
    transformations = []
    statistics = []

    for column in selected:
        original = result[column].copy()

        result[column] = result[column].map(
            lambda value: _normalize_value(
                value, operations, unicode_form
            )
        )

        changed_mask = (
            original.astype("object").fillna("__DATAFORGE_NULL__")
            != result[column].astype("object").fillna(
                "__DATAFORGE_NULL__"
            )
        )

        changed_count = int(changed_mask.sum())

        transformations.append({
            "operation": "string_normalization",
            "column": column,
            "applied_operations": operations.copy(),
            "unicode_form": (
                unicode_form if "unicode" in operations else None
            ),
            "values_changed": changed_count,
            "rows_before": len(dataframe),
            "rows_after": len(result),
        })

        statistics.append({
            "column": column,
            "values_changed": changed_count,
            "missing_before": int(original.isna().sum()),
            "missing_after": int(result[column].isna().sum()),
        })

    return StringNormalizationResult(
        dataframe=result,
        transformations=transformations,
        statistics=pd.DataFrame(statistics),
    )


def normalize_categorical_labels(
    dataframe: pd.DataFrame,
    columns: list[str],
    lowercase: bool = True,
) -> StringNormalizationResult:
    """Normalize categorical labels using whitespace and case rules."""

    if not isinstance(lowercase, bool):
        raise TypeError("lowercase must be a boolean.")

    operations = ["strip", "collapse_whitespace"]

    if lowercase:
        operations.append("lowercase")

    return normalize_strings(
        dataframe,
        columns=columns,
        operations=operations,
    )
