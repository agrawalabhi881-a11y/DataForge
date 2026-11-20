"""DataForge - Data Engineering: completeness metrics."""
import pandas as pd


def assess_completeness(df: pd.DataFrame, required_columns=None) -> dict:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a DataFrame")
    if not df.columns.is_unique:
        raise ValueError("Duplicate column names")
    required = list(required_columns) if required_columns is not None else list(df.columns)
    if len(required) != len(set(required)):
        raise ValueError("Duplicate required columns")
    missing = [c for c in required if c not in df.columns]
    total = len(df) * len(required)
    present = sum(int(df[c].notna().sum()) for c in required if c in df)
    return {"score": round(100 * present / total, 2) if total else 100.0,
            "missing_required_columns": missing,
            "missing_by_column": {c: int(df[c].isna().sum()) if c in df else len(df) for c in required},
            "record_count": len(df)}
