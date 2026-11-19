
"""
DataForge - Data Engineering
Module: Missing Value Handling

Analyze and handle missing values while preserving
the original dataset and recording transformations.
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class MissingValueResult:
    """Store cleaned data, statistics, and transformation history."""

    dataframe: pd.DataFrame
    statistics: pd.DataFrame
    transformations: list[dict[str, Any]]


def analyze_missing_values(
    dataframe: pd.DataFrame,
    threshold: float = 50.0,
) -> pd.DataFrame:
    """Calculate missing-value statistics for every column."""

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a Pandas DataFrame.")

    if not 0 <= threshold <= 100:
        raise ValueError("threshold must be between 0 and 100.")

    if not dataframe.columns.is_unique:
        raise ValueError("DataFrame column names must be unique.")

    total_rows = len(dataframe)
    missing_counts = dataframe.isna().sum()

    if total_rows == 0:
        percentages = pd.Series(
            0.0, index=dataframe.columns
        )
    else:
        percentages = missing_counts / total_rows * 100

    return pd.DataFrame({
        "column": dataframe.columns,
        "missing_count": missing_counts.to_numpy(),
        "missing_percentage": percentages.to_numpy(),
        "exceeds_threshold": (
            percentages > threshold
        ).to_numpy(),
    })


def get_high_missing_columns(
    dataframe: pd.DataFrame,
    threshold: float = 50.0,
) -> list[str]:
    """Identify columns exceeding the missing-value threshold."""

    statistics = analyze_missing_values(
        dataframe, threshold
    )

    return statistics.loc[
        statistics["exceeds_threshold"], "column"
    ].tolist()


def handle_missing_values(
    dataframe: pd.DataFrame,
    strategy: str = "none",
    columns: list[str] | None = None,
    fill_value: Any = None,
) -> MissingValueResult:
    """
    Apply a selected missing-value handling strategy.

    Supported strategies:
    none, drop_rows, drop_columns, constant,
    mean, median, mode.
    """

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a Pandas DataFrame.")

    if not dataframe.columns.is_unique:
        raise ValueError("DataFrame column names must be unique.")

    supported = {
        "none",
        "drop_rows",
        "drop_columns",
        "constant",
        "mean",
        "median",
        "mode",
    }

    if strategy not in supported:
        raise ValueError(
            f"Unsupported strategy: {strategy}. "
            f"Choose from {sorted(supported)}"
        )

    if columns is None:
        selected_columns = dataframe.columns.tolist()
    else:
        if not isinstance(columns, list) or not all(
            isinstance(column, str) for column in columns
        ):
            raise TypeError("columns must be a list of strings.")

        if len(columns) != len(set(columns)):
            raise ValueError("Duplicate column names are not allowed.")

        missing_columns = [
            column for column in columns
            if column not in dataframe.columns
        ]

        if missing_columns:
            raise ValueError(
                f"Columns not found: {missing_columns}"
            )

        selected_columns = columns

    cleaned = dataframe.copy(deep=True)
    transformations = []

    before_rows = len(cleaned)
    before_missing = int(
        cleaned[selected_columns].isna().sum().sum()
    )

    if strategy == "drop_rows":
        cleaned = cleaned.dropna(
            subset=selected_columns
        ).copy()

    elif strategy == "drop_columns":
        columns_to_drop = [
            column for column in selected_columns
            if cleaned[column].isna().any()
        ]

        cleaned = cleaned.drop(
            columns=columns_to_drop
        )

    elif strategy == "constant":
        if fill_value is None:
            raise ValueError(
                "fill_value is required for constant strategy."
            )

        for column in selected_columns:
            cleaned[column] = cleaned[column].fillna(
                fill_value
            )

    elif strategy in {"mean", "median"}:
        for column in selected_columns:
            if not cleaned[column].isna().any():
                continue

            if not pd.api.types.is_numeric_dtype(
                cleaned[column]
            ):
                raise TypeError(
                    f"Column '{column}' must be numeric "
                    f"for {strategy} imputation."
                )

            if strategy == "mean":
                replacement = cleaned[column].mean()
            else:
                replacement = cleaned[column].median()

            if pd.isna(replacement):
                raise ValueError(
                    f"Cannot calculate {strategy} "
                    f"for column '{column}'."
                )

            cleaned[column] = cleaned[column].fillna(
                replacement
            )

    elif strategy == "mode":
        for column in selected_columns:
            if not cleaned[column].isna().any():
                continue

            modes = cleaned[column].mode(dropna=True)

            if modes.empty:
                raise ValueError(
                    f"Cannot calculate mode for "
                    f"column '{column}'."
                )

            cleaned[column] = cleaned[column].fillna(
                modes.iloc[0]
            )

    after_missing = int(
        cleaned[
            [c for c in selected_columns if c in cleaned.columns]
        ].isna().sum().sum()
    )

    transformations.append({
        "operation": "missing_value_handling",
        "strategy": strategy,
        "columns": selected_columns,
        "fill_value": (
            repr(fill_value) if strategy == "constant"
            else None
        ),
        "rows_before": before_rows,
        "rows_after": len(cleaned),
        "rows_removed": before_rows - len(cleaned),
        "missing_before": before_missing,
        "missing_after": after_missing,
        "missing_resolved": before_missing - after_missing,
    })

    return MissingValueResult(
        dataframe=cleaned,
        statistics=analyze_missing_values(cleaned),
        transformations=transformations,
    )
