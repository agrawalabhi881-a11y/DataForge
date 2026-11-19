
"""
DataForge - Data Engineering
Module: Outlier Detection

Identify statistical outliers without automatically removing
potentially important cybersecurity observations.
"""

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class OutlierResult:
    dataframe: pd.DataFrame
    outlier_records: pd.DataFrame
    statistics: pd.DataFrame
    transformations: list[dict[str, Any]]


def _validate_input(
    dataframe: pd.DataFrame,
    columns: list[str] | None,
    method: str,
    threshold: float,
) -> list[str]:
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a Pandas DataFrame.")

    if not dataframe.columns.is_unique:
        raise ValueError("DataFrame column names must be unique.")

    if method not in {"iqr", "zscore"}:
        raise ValueError("method must be 'iqr' or 'zscore'.")

    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not np.isfinite(threshold)
        or threshold <= 0
    ):
        raise ValueError("threshold must be a positive finite number.")

    if columns is None:
        selected = dataframe.select_dtypes(
            include="number"
        ).columns.tolist()
    else:
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

        selected = columns

    if not selected:
        raise ValueError("No numeric columns available for analysis.")

    for column in selected:
        if not pd.api.types.is_numeric_dtype(dataframe[column]):
            raise TypeError(f"Column '{column}' must be numeric.")

        if pd.api.types.is_bool_dtype(dataframe[column]):
            raise TypeError(f"Column '{column}' must not be boolean.")

    return selected


def _calculate_outlier_mask(
    series: pd.Series,
    method: str,
    threshold: float,
) -> tuple[pd.Series, float | None, float | None]:
    numeric = pd.to_numeric(series, errors="raise")
    values = numeric.to_numpy(dtype=float, na_value=np.nan)

    if np.isinf(values).any():
        raise ValueError("Infinite values cannot be analyzed.")

    valid = values[np.isfinite(values)]
    mask = np.zeros(len(values), dtype=bool)

    if len(valid) < 2:
        return pd.Series(mask, index=series.index), None, None

    if method == "iqr":
        q1, q3 = np.percentile(valid, [25, 75])
        iqr = q3 - q1

        lower = float(q1 - threshold * iqr)
        upper = float(q3 + threshold * iqr)

        mask = np.isfinite(values) & (
            (values < lower) | (values > upper)
        )

    else:
        mean = float(np.mean(valid))
        std = float(np.std(valid, ddof=0))

        if std == 0:
            return pd.Series(mask, index=series.index), None, None

        lower = mean - threshold * std
        upper = mean + threshold * std

        mask = np.isfinite(values) & (
            (values < lower) | (values > upper)
        )

    return (
        pd.Series(mask, index=series.index),
        lower,
        upper,
    )


def analyze_outliers(
    dataframe: pd.DataFrame,
    columns: list[str] | None = None,
    method: str = "iqr",
    threshold: float | None = None,
) -> pd.DataFrame:
    """Calculate outlier statistics for selected numeric columns."""

    if threshold is None:
        threshold = 1.5 if method == "iqr" else 3.0

    selected = _validate_input(
        dataframe, columns, method, threshold
    )

    records = []

    for column in selected:
        mask, lower, upper = _calculate_outlier_mask(
            dataframe[column], method, threshold
        )

        count = int(mask.sum())
        total = len(dataframe)

        records.append({
            "column": column,
            "method": method,
            "threshold": threshold,
            "lower_bound": lower,
            "upper_bound": upper,
            "outlier_count": count,
            "outlier_percentage": (
                round(count / total * 100, 2)
                if total else 0.0
            ),
        })

    return pd.DataFrame(records)


def detect_outliers(
    dataframe: pd.DataFrame,
    columns: list[str] | None = None,
    method: str = "iqr",
    threshold: float | None = None,
) -> OutlierResult:
    """
    Flag outliers and return matching records.

    The original dataset and all observations are preserved.
    """

    if threshold is None:
        threshold = 1.5 if method == "iqr" else 3.0

    selected = _validate_input(
        dataframe, columns, method, threshold
    )

    result = dataframe.copy(deep=True)
    combined_mask = np.zeros(len(result), dtype=bool)

    statistics = analyze_outliers(
        dataframe,
        columns=selected,
        method=method,
        threshold=threshold,
    )

    for column in selected:
        mask, _, _ = _calculate_outlier_mask(
            dataframe[column], method, threshold
        )

        flag_column = f"{column}_is_outlier"

        if flag_column in result.columns:
            raise ValueError(
                f"Flag column already exists: {flag_column}"
            )

        result[flag_column] = mask.to_numpy()
        combined_mask |= mask.to_numpy()

    outlier_records = result.iloc[
        np.flatnonzero(combined_mask)
    ].copy(deep=True)

    transformations = [{
        "operation": "outlier_detection",
        "method": method,
        "threshold": threshold,
        "columns": selected,
        "rows_before": len(dataframe),
        "rows_after": len(result),
        "rows_removed": 0,
        "flagged_records": int(combined_mask.sum()),
        "action": "flag_only",
    }]

    return OutlierResult(
        dataframe=result,
        outlier_records=outlier_records,
        statistics=statistics,
        transformations=transformations,
    )
