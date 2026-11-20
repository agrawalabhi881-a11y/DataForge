"""DataForge - Data Engineering: requested feature coverage."""
import pandas as pd


def assess_feature_coverage(df: pd.DataFrame, required_features: list[str]) -> dict:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a DataFrame")
    if not isinstance(required_features, list) or len(required_features) != len(set(required_features)) or not all(isinstance(x, str) for x in required_features):
        raise ValueError("required_features must be a unique list of strings")
    present = [x for x in required_features if x in df]
    missing = [x for x in required_features if x not in df]
    return {"score": round(100 * len(present) / len(required_features), 2) if required_features else 100.0,
            "present_features": present, "missing_features": missing,
            "extra_features": [x for x in df if x not in required_features]}
