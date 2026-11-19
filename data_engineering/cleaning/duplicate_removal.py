
"""
DataForge - Data Engineering
Module: Duplicate Detection and Removal

Detect exact and key-based duplicate records without
modifying the original dataset.
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class DuplicateResult:
    dataframe: pd.DataFrame
    duplicate_records: pd.DataFrame
    statistics: dict[str, Any]
    transformations: list[dict[str, Any]]


def _validate_dataframe(dataframe: pd.DataFrame) -> None:
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a Pandas DataFrame.")

    if not dataframe.columns.is_unique:
        raise ValueError("DataFrame column names must be unique.")


def _validate_subset(
    dataframe: pd.DataFrame,
    subset: list[str] | None,
) -> list[str] | None:
    if subset is None:
        return None

    if (
        not isinstance(subset, list)
        or not subset
        or not all(isinstance(c, str) for c in subset)
    ):
        raise TypeError("subset must be a non-empty list of strings.")

    if len(subset) != len(set(subset)):
        raise ValueError("Duplicate subset columns are not allowed.")

    missing = [c for c in subset if c not in dataframe.columns]

    if missing:
        raise ValueError(f"Columns not found: {missing}")

    return subset


def analyze_duplicates(
    dataframe: pd.DataFrame,
    subset: list[str] | None = None,
) -> dict[str, Any]:
    """Calculate duplicate statistics."""

    _validate_dataframe(dataframe)
    subset = _validate_subset(dataframe, subset)

    total = len(dataframe)

    if dataframe.shape[1] == 0 and subset is None:
        raise ValueError("DataFrame must contain at least one column.")

    duplicate_mask = dataframe.duplicated(
        subset=subset,
        keep="first",
    )

    duplicate_count = int(duplicate_mask.sum())

    duplicate_groups_mask = dataframe.duplicated(
        subset=subset,
        keep=False,
    )

    return {
        "total_records": total,
        "duplicate_records": duplicate_count,
        "duplicate_percentage": (
            round(duplicate_count / total * 100, 2)
            if total else 0.0
        ),
        "records_in_duplicate_groups": int(
            duplicate_groups_mask.sum()
        ),
        "unique_records": total - duplicate_count,
        "subset": subset,
    }


def detect_duplicates(
    dataframe: pd.DataFrame,
    subset: list[str] | None = None,
    keep: str | bool = False,
) -> pd.DataFrame:
    """Return records identified as duplicates."""

    _validate_dataframe(dataframe)
    subset = _validate_subset(dataframe, subset)

    if keep not in ("first", "last", False):
        raise ValueError(
            "keep must be 'first', 'last', or False."
        )

    if dataframe.shape[1] == 0 and subset is None:
        raise ValueError("DataFrame must contain at least one column.")

    mask = dataframe.duplicated(
        subset=subset,
        keep=keep,
    )

    return dataframe.loc[mask].copy(deep=True)


def remove_duplicates(
    dataframe: pd.DataFrame,
    subset: list[str] | None = None,
    keep: str | bool = "first",
    reset_index: bool = True,
) -> DuplicateResult:
    """
    Remove duplicates using an explicit retention rule.

    subset=None checks entire records.
    subset=['column'] checks selected identity fields.
    """

    _validate_dataframe(dataframe)
    subset = _validate_subset(dataframe, subset)

    if keep not in ("first", "last", False):
        raise ValueError(
            "keep must be 'first', 'last', or False."
        )

    if not isinstance(reset_index, bool):
        raise TypeError("reset_index must be a boolean.")

    statistics = analyze_duplicates(
        dataframe, subset=subset
    )

    removed_mask = dataframe.duplicated(
        subset=subset,
        keep=keep,
    )

    removed_records = dataframe.loc[
        removed_mask
    ].copy(deep=True)

    cleaned = dataframe.drop_duplicates(
        subset=subset,
        keep=keep,
    ).copy(deep=True)

    if reset_index:
        cleaned = cleaned.reset_index(drop=True)

    transformations = [{
        "operation": "duplicate_removal",
        "subset": subset,
        "keep": keep,
        "rows_before": len(dataframe),
        "rows_after": len(cleaned),
        "rows_removed": len(removed_records),
        "duplicate_percentage": statistics[
            "duplicate_percentage"
        ],
    }]

    return DuplicateResult(
        dataframe=cleaned,
        duplicate_records=removed_records,
        statistics=statistics,
        transformations=transformations,
    )
