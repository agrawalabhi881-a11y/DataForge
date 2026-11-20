"""DataForge - Data Engineering: translate sufficiency gaps into a planning report."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def calculate_augmentation_requirements(sufficiency_report: Mapping[str, Any]) -> dict[str, Any]:
    """Summarize deficits for the strategy engine; do not synthesize records."""
    if not isinstance(sufficiency_report, Mapping):
        raise TypeError("sufficiency_report must be a mapping")
    needed = {"domain", "required_records", "available_real_records", "missing_features", "missing_or_insufficient_labels", "class_distribution", "unmet_requirements"}
    missing = needed.difference(sufficiency_report)
    if missing:
        raise ValueError(f"Sufficiency report missing keys: {sorted(missing)}")
    required = sufficiency_report["required_records"]
    available = sufficiency_report["available_real_records"]
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in (required, available)):
        raise ValueError("Record counts must be nonnegative integers")
    gaps = list(sufficiency_report["unmet_requirements"])
    return {
        "domain": sufficiency_report["domain"],
        "additional_records_needed": max(0, required - available),
        "missing_features": list(sufficiency_report["missing_features"]),
        "missing_or_insufficient_labels": list(sufficiency_report["missing_or_insufficient_labels"]),
        "current_class_distribution": dict(sufficiency_report["class_distribution"]),
        "unmet_requirements": gaps,
        "augmentation_candidate": bool(gaps),
        "recommended_next_step": "review_quality_and_data_options" if gaps else "no_requirement_gap_detected",
        "notes": [
            "Additional records needed is a count shortfall, not a synthetic generation instruction.",
            "Missing features may require schema enrichment or additional real sources, not generated values.",
            "The adaptive strategy engine decides real-only, hybrid, or synthetic-only delivery.",
        ],
    }


get_augmentation_requirements = calculate_augmentation_requirements
