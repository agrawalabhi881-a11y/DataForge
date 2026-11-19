from pydantic import BaseModel, Field


class DecisionConfig(BaseModel):
    # Step 1: is the real data usable at all? (failing any => synthetic_only)
    min_relevance: float = Field(0.30, ge=0, le=1)
    min_quality_per_dimension: float = Field(0.50, ge=0, le=1)
    min_feature_coverage_for_real: float = Field(0.50, ge=0, le=1)
    min_label_coverage_for_real: float = Field(0.50, ge=0, le=1)
    # A source is NEVER eligible until its license is verified.
    allowed_license_statuses: tuple[str, ...] = ("verified_open",)

    # Step 2: is the real data enough on its own? (failing any => real_plus_synthetic)
    min_record_ratio: float = Field(1.0, ge=0, le=1)
    min_feature_coverage: float = Field(1.0, ge=0, le=1)
    # Each required label should be at least this share of the final dataset
    # (capped at 1 / number_of_labels so many labels stay possible).
    min_class_share: float = Field(0.10, ge=0, le=1)

    # Below this, quality only gives a warning (synthetic data cannot repair real records)
    acceptable_quality: float = Field(0.80, ge=0, le=1)


DEFAULT_CONFIG = DecisionConfig()