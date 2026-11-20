"""DataForge - Data Engineering: validate datasets against explicit canonical schemas."""
from dataclasses import dataclass
from typing import Any
import pandas as pd

@dataclass
class SchemaValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]
    statistics: dict[str, Any]


def validate_schema(
    dataframe: pd.DataFrame,
    required_columns: list[str],
    column_types: dict[str, str] | None = None,
    nullable_columns: list[str] | None = None,
    allow_extra_columns: bool = True,
    schema_version: str = "1.0",
) -> SchemaValidationResult:
    """Report missing fields, nulls, type mismatches, and extra fields without mutation."""
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a Pandas DataFrame.")
    if not dataframe.columns.is_unique:
        raise ValueError("DataFrame column names must be unique.")
    if not isinstance(required_columns, list) or not all(isinstance(c, str) and c.strip() for c in required_columns):
        raise TypeError("required_columns must be a list of non-empty strings.")
    if len(set(required_columns)) != len(required_columns):
        raise ValueError("required_columns must not contain duplicates.")
    if column_types is not None and not isinstance(column_types, dict):
        raise TypeError("column_types must be a dictionary.")
    if nullable_columns is not None and (not isinstance(nullable_columns, list) or not all(isinstance(c, str) for c in nullable_columns)):
        raise TypeError("nullable_columns must be a list of strings.")
    if not isinstance(allow_extra_columns, bool):
        raise TypeError("allow_extra_columns must be a boolean.")
    if not isinstance(schema_version, str) or not schema_version.strip():
        raise ValueError("schema_version must be a non-empty string.")

    errors: list[str] = []
    warnings: list[str] = []
    nullable = set(nullable_columns or [])
    expected = set(required_columns) | set(column_types or {})
    missing = [c for c in required_columns if c not in dataframe.columns]
    for column in missing:
        errors.append(f"Missing required column: {column}")
    extra = [c for c in dataframe.columns if c not in expected]
    if extra:
        (warnings if allow_extra_columns else errors).append(f"Extra columns: {extra}")

    for column in required_columns:
        if column in dataframe.columns and column not in nullable:
            count = int(dataframe[column].isna().sum())
            if count:
                errors.append(f"Required column '{column}' contains {count} missing values")

    supported = {"integer", "float", "string", "boolean", "datetime"}
    for column, expected_type in (column_types or {}).items():
        if expected_type not in supported:
            raise ValueError(f"Unsupported expected type for '{column}': {expected_type}")
        if column not in dataframe.columns:
            errors.append(f"Missing typed column: {column}")
            continue
        dtype = dataframe[column].dtype
        checks = {
            "integer": pd.api.types.is_integer_dtype,
            "float": pd.api.types.is_float_dtype,
            "string": pd.api.types.is_string_dtype,
            "boolean": pd.api.types.is_bool_dtype,
            "datetime": pd.api.types.is_datetime64_any_dtype,
        }
        if not checks[expected_type](dtype):
            errors.append(f"Column '{column}' has dtype {dtype}; expected {expected_type}")

    return SchemaValidationResult(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        statistics={
            "schema_version": schema_version,
            "record_count": len(dataframe),
            "column_count": len(dataframe.columns),
            "missing_required_columns": missing,
            "extra_columns": extra,
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
    )
