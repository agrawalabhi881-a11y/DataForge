"""DataForge - Data Engineering: uniqueness metrics."""
import pandas as pd


def assess_uniqueness(df: pd.DataFrame, subset: list[str] | None = None) -> dict:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a DataFrame")
    if not df.columns.is_unique:
        raise ValueError("Duplicate column names")
    if subset is not None and (not subset or len(subset) != len(set(subset)) or any(c not in df for c in subset)):
        raise ValueError("Invalid subset")
    if df.shape[1] == 0:
        return {"score": 100.0, "duplicate_records": 0, "record_count": len(df)} if df.empty else {"score": 0.0, "duplicate_records": len(df), "record_count": len(df)}
    count = int(df.duplicated(subset=subset).sum())
    return {"score": round(100 * (len(df) - count) / len(df), 2) if len(df) else 100.0,
            "duplicate_records": count, "record_count": len(df)}
