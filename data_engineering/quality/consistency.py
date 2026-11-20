"""DataForge - Data Engineering: consistency metrics."""
import pandas as pd


def assess_consistency(df: pd.DataFrame, allowed_values: dict | None = None) -> dict:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a DataFrame")
    if not df.columns.is_unique:
        raise ValueError("Duplicate column names")
    allowed_values = {} if allowed_values is None else allowed_values
    if not isinstance(allowed_values, dict):
        raise TypeError("allowed_values must be a dictionary")
    for col in allowed_values:
        if col not in df:
            raise ValueError(f"Missing consistency column: {col}")
    violations = {col: int((df[col].notna() & ~df[col].isin(values)).sum()) for col, values in allowed_values.items()}
    checked = sum(int(df[col].notna().sum()) for col in allowed_values)
    return {"score": round(100 * (checked - sum(violations.values())) / checked, 2) if checked else 100.0,
            "violations_by_column": violations, "checked_values": checked}
