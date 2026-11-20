"""DataForge - Data Engineering: inspect and validate externally supplied column mappings."""
from dataclasses import dataclass
from typing import Any
import pandas as pd

@dataclass
class ColumnMappingResult:
    mapping: dict[str, str]
    unmapped_columns: list[str]
    missing_sources: list[str]
    conflicts: list[str]
    warnings: list[str]
    valid: bool


def inspect_column_mapping(
    dataframe: pd.DataFrame,
    mapping: dict[str, str],
    canonical_columns: list[str] | None = None,
    confidence: dict[str, float] | None = None,
    minimum_confidence: float = 0.8,
) -> ColumnMappingResult:
    """Flag missing, ambiguous, or low-confidence mappings; never infer field meanings."""
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a Pandas DataFrame.")
    if not dataframe.columns.is_unique:
        raise ValueError("Source column names must be unique.")
    if not isinstance(mapping, dict) or not all(
        isinstance(k, str) and k.strip() and isinstance(v, str) and v.strip()
        for k, v in mapping.items()
    ):
        raise ValueError("mapping must contain non-empty string names.")
    if canonical_columns is not None and (
        not isinstance(canonical_columns, list)
        or not all(isinstance(c, str) and c.strip() for c in canonical_columns)
        or len(canonical_columns) != len(set(canonical_columns))
    ):
        raise ValueError("canonical_columns must be unique, non-empty strings.")
    if confidence is not None and not isinstance(confidence, dict):
        raise TypeError("confidence must be a dictionary.")
    if isinstance(minimum_confidence, bool) or not isinstance(minimum_confidence, (int, float)) or not 0 <= minimum_confidence <= 1:
        raise ValueError("minimum_confidence must be between 0 and 1.")

    missing = [source for source in mapping if source not in dataframe.columns]
    unmapped = [column for column in dataframe.columns if column not in mapping]
    conflicts: list[str] = []
    warnings: list[str] = []
    seen: dict[str, str] = {}
    for source, target in mapping.items():
        if target in seen:
            conflicts.append(f"'{source}' and '{seen[target]}' both map to '{target}'")
        else:
            seen[target] = source
        if canonical_columns is not None and target not in canonical_columns:
            conflicts.append(f"Target '{target}' is not in the canonical schema")
    output_names = [mapping.get(c, c) for c in dataframe.columns]
    if len(output_names) != len(set(output_names)):
        conflicts.append("Mapping collides with an existing output column")
    if confidence:
        for source, score in confidence.items():
            if source not in mapping:
                warnings.append(f"Confidence supplied for unmapped source '{source}'")
                continue
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 1:
                conflicts.append(f"Invalid confidence for '{source}'")
            elif score < minimum_confidence:
                warnings.append(f"Low-confidence mapping for '{source}': {score}")
    if missing:
        warnings.append(f"Missing source columns: {missing}")
    if unmapped:
        warnings.append(f"Unmapped source columns: {unmapped}")
    return ColumnMappingResult(
        mapping.copy(), unmapped, missing, conflicts, warnings,
        valid=not (missing or conflicts or any(w.startswith("Low-confidence") for w in warnings)),
    )


def require_valid_mapping(result: ColumnMappingResult) -> dict[str, str]:
    """Return the supplied mapping only if validation found no blocking issues."""
    if not isinstance(result, ColumnMappingResult):
        raise TypeError("result must be a ColumnMappingResult.")
    if not result.valid:
        raise ValueError(f"Mapping requires review: {result.conflicts + result.warnings}")
    return result.mapping.copy()
