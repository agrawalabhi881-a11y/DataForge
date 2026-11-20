"""DataForge - Data Engineering: evidence-based dataset sufficiency checks."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd


def _names(values: Sequence[str] | None, name: str) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise TypeError(f"{name} must be a sequence of column/label names")
    result = list(values)
    if any(not isinstance(v, str) or not v.strip() for v in result):
        raise ValueError(f"{name} must contain nonempty strings")
    if len(set(result)) != len(result):
        raise ValueError(f"{name} must not contain duplicates")
    return result


def check_dataset_sufficiency(
    dataframe: pd.DataFrame,
    *,
    domain: str,
    required_records: int,
    required_features: Sequence[str] | None = None,
    required_labels: Sequence[str] | None = None,
    label_column: str = "label",
    minimum_class_counts: Mapping[str, int] | None = None,
    invalid_record_count: int | None = None,
    duplicate_subset: Sequence[str] | None = None,
    maximum_missing_percentage: float | None = None,
    maximum_invalid_percentage: float | None = None,
    maximum_duplicate_percentage: float | None = None,
    quality_status: str | None = None,
) -> dict[str, Any]:
    """Report unmet requirements; do not select the adaptive strategy.

    Invalid records cannot be inferred reliably without domain validation, so
    invalid_record_count=None produces an unknown metric, not an invented zero.
    """
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a pandas DataFrame")
    if not dataframe.columns.is_unique:
        raise ValueError("DataFrame columns must be unique")
    if not isinstance(domain, str) or not domain.strip():
        raise ValueError("domain must be a nonempty string")
    if isinstance(required_records, bool) or not isinstance(required_records, int) or required_records < 0:
        raise ValueError("required_records must be a nonnegative integer")
    if not isinstance(label_column, str) or not label_column:
        raise ValueError("label_column must be a nonempty string")
    features = _names(required_features, "required_features")
    labels = _names(required_labels, "required_labels")
    subset = _names(duplicate_subset, "duplicate_subset")
    missing_subset = [c for c in subset if c not in dataframe.columns]
    if missing_subset:
        raise ValueError(f"duplicate_subset columns not found: {missing_subset}")
    if minimum_class_counts is not None:
        if not isinstance(minimum_class_counts, Mapping):
            raise TypeError("minimum_class_counts must be a mapping")
        for label, count in minimum_class_counts.items():
            if not isinstance(label, str) or not label or isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError("minimum_class_counts requires nonnegative integer counts keyed by labels")
    for name, value in (("maximum_missing_percentage", maximum_missing_percentage),
                        ("maximum_invalid_percentage", maximum_invalid_percentage),
                        ("maximum_duplicate_percentage", maximum_duplicate_percentage)):
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100):
            raise ValueError(f"{name} must be between 0 and 100")
    if invalid_record_count is not None and (isinstance(invalid_record_count, bool) or not isinstance(invalid_record_count, int) or not 0 <= invalid_record_count <= len(dataframe)):
        raise ValueError("invalid_record_count must be between 0 and row count")

    count = len(dataframe)
    available = [c for c in features if c in dataframe.columns]
    missing = [c for c in features if c not in dataframe.columns]
    if label_column in dataframe.columns:
        class_counts = {str(k): int(v) for k, v in dataframe[label_column].value_counts(dropna=True).items()}
    else:
        class_counts = {}
    min_counts = dict(minimum_class_counts or {})
    insufficient_labels = [label for label in labels if class_counts.get(label, 0) < max(1, min_counts.get(label, 0))]
    insufficient_labels.extend(label for label in min_counts if label not in labels and class_counts.get(label, 0) < min_counts[label])
    missing_cells = int(dataframe.isna().sum().sum())
    total_cells = count * len(dataframe.columns)
    missing_pct = round(100 * missing_cells / total_cells, 2) if total_cells else 0.0
    duplicates = int(dataframe.duplicated(subset=subset or None).sum())
    duplicate_pct = round(100 * duplicates / count, 2) if count else 0.0
    invalid_pct = round(100 * invalid_record_count / count, 2) if count and invalid_record_count is not None else (0.0 if invalid_record_count == 0 else None)
    gaps = []
    if count < required_records:
        gaps.append("insufficient_records")
    if missing:
        gaps.append("missing_features")
    if insufficient_labels:
        gaps.append("insufficient_labels")
    if maximum_missing_percentage is not None and missing_pct > maximum_missing_percentage:
        gaps.append("excessive_missing_values")
    if maximum_duplicate_percentage is not None and duplicate_pct > maximum_duplicate_percentage:
        gaps.append("excessive_duplicates")
    if maximum_invalid_percentage is not None:
        if invalid_pct is None:
            gaps.append("invalidity_not_assessed")
        elif invalid_pct > maximum_invalid_percentage:
            gaps.append("excessive_invalid_records")
    if quality_status is not None and quality_status not in {"good", "acceptable", "passed"}:
        gaps.append("quality_not_approved")
    if not isinstance(quality_status, (str, type(None))):
        raise TypeError("quality_status must be a string or None")
    meets = not gaps
    return {
        "domain": domain,
        "required_records": required_records,
        "available_real_records": count,
        "record_shortfall": max(0, required_records - count),
        "required_features": len(features),
        "available_required_features": len(available),
        "available_features": available,
        "missing_features": missing,
        "required_labels": labels,
        "class_distribution": class_counts,
        "missing_or_insufficient_labels": insufficient_labels,
        "missing_value_percentage": missing_pct,
        "invalid_record_percentage": invalid_pct,
        "duplicate_record_percentage": duplicate_pct,
        "invalid_record_count": invalid_record_count,
        "duplicate_record_count": duplicates,
        "augmentation_required": bool(gaps),
        "meets_requirements": meets,
        "unmet_requirements": gaps,
        "quality_status": quality_status or ("needs_improvement" if gaps else "requirements_met_quality_unassessed"),
        "notes": ["Augmentation required means unmet requirements exist; it is not a decision to generate synthetic data.",
                  "Invalidity is unknown unless invalid_record_count is provided.",
                  "Row count is the input dataset size; ensure it contains only real records before using available_real_records."],
    }


analyze_sufficiency = check_dataset_sufficiency
