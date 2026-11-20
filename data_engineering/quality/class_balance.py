"""DataForge - Data Engineering: descriptive class balance (no resampling)."""
import pandas as pd


def assess_class_balance(df: pd.DataFrame, label_column: str = "label") -> dict:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a DataFrame")
    if label_column not in df or not df.columns.is_unique:
        raise ValueError("Label column missing or duplicate column names")
    counts = df[label_column].value_counts(dropna=False)
    distribution = {str(k) if pd.notna(k) else "<missing>": int(v) for k, v in counts.items()}
    nonmissing = df[label_column].dropna().value_counts()
    ratio = round(float(nonmissing.min() / nonmissing.max()), 4) if len(nonmissing) >= 2 and nonmissing.max() else None
    return {"distribution": distribution, "minority_majority_ratio": ratio,
            "missing_labels": int(df[label_column].isna().sum()), "record_count": len(df)}
