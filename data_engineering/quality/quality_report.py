"""DataForge - Data Engineering: structured quality reporting."""
from typing import Any
import pandas as pd
from .completeness import assess_completeness
from .validity import assess_validity
from .uniqueness import assess_uniqueness
from .consistency import assess_consistency
from .class_balance import assess_class_balance
from .feature_coverage import assess_feature_coverage


def generate_quality_report(
    df: pd.DataFrame,
    *,
    dataset_id: str | None = None,
    domain: str | None = None,
    required_columns: list[str] | None = None,
    required_features: list[str] | None = None,
    validity_rules: dict[str, str] | None = None,
    allowed_values: dict[str, Any] | None = None,
    unique_subset: list[str] | None = None,
    label_column: str | None = "label",
    minimum_score: float = 90.0,
) -> dict:
    """Report measured dimensions only; no unsupported quality claims."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a DataFrame")
    if not 0 <= minimum_score <= 100:
        raise ValueError("minimum_score must be between 0 and 100")
    metrics = {
        "completeness": assess_completeness(df, required_columns),
        "validity": assess_validity(df, validity_rules),
        "uniqueness": assess_uniqueness(df, unique_subset),
        "consistency": assess_consistency(df, allowed_values),
    }
    if required_features is not None:
        metrics["feature_coverage"] = assess_feature_coverage(df, required_features)
    if label_column is not None and label_column in df:
        metrics["class_balance"] = assess_class_balance(df, label_column)
    scores = [v["score"] for v in metrics.values() if "score" in v]
    overall = round(sum(scores) / len(scores), 2) if scores else None
    warnings = []
    if not validity_rules:
        warnings.append("No validity rules supplied; validity is not substantively assessed")
    if not allowed_values:
        warnings.append("No consistency rules supplied; consistency is not substantively assessed")
    if required_features is None:
        warnings.append("Required features not supplied; feature coverage not assessed")
    status = "needs_review" if warnings else ("validated" if overall is not None and overall >= minimum_score else "needs_improvement")
    return {"dataset_id": dataset_id, "domain": domain, "record_count": len(df),
            "quality_status": status, "overall_score": overall,
            "metrics": metrics, "warnings": warnings}
