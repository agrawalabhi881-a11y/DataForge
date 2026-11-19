from app.adaptive_engine import sufficiency_checker as check
from app.adaptive_engine.decision_config import DEFAULT_CONFIG, DecisionConfig
from app.schemas.strategy import (
    GenerationPlan,
    RealDataAssessment,
    Requirements,
    SourceEligibility,
    StrategyDecision,
)


def select_strategy(
    requirements: Requirements,
    assessment: RealDataAssessment,
    sources: list[SourceEligibility],
    config: DecisionConfig = DEFAULT_CONFIG,
) -> StrategyDecision:
    target = requirements.record_count
    available = assessment.available_record_count
    required_labels = check._unique(requirements.required_labels)
    required_features = check._unique(requirements.required_features)

    feature_coverage, missing_features = check.feature_gap(
        required_features, assessment.available_features
    )
    label_coverage, missing_labels, counts = check.label_gap(
        required_labels, assessment.label_counts
    )
    eligible_ids, source_problems = check.split_sources(sources, config)

    metrics = {
        "target_records": target,
        "available_real_records": available,
        "record_ratio": round(available / target, 4),
        "feature_coverage": round(feature_coverage, 4),
        "label_coverage": round(label_coverage, 4),
        "quality": check.quality_scores(assessment),
        "relevance": assessment.relevance,
        "eligible_sources": len(eligible_ids),
    }
    warnings = list(source_problems)

    # ---------------- Step 1: is the real data usable at all? ----------------
    unsuitable = []
    if not eligible_ids:
        unsuitable.append("No eligible real source (needs: acquired, license verified, access OK)")
    if available == 0:
        unsuitable.append("There are no usable real records")
    if assessment.relevance < config.min_relevance:
        unsuitable.append(
            f"Real data relevance {assessment.relevance} is below {config.min_relevance}"
        )
    for name in check.dimensions_below(assessment, config.min_quality_per_dimension):
        unsuitable.append(f"Real data {name} is below {config.min_quality_per_dimension}")
    if feature_coverage < config.min_feature_coverage_for_real:
        unsuitable.append(
            f"Real data has only {feature_coverage:.0%} of the required features "
            f"(needs at least {config.min_feature_coverage_for_real:.0%})"
        )
    if required_labels and label_coverage < config.min_label_coverage_for_real:
        unsuitable.append(
            f"Real data has only {label_coverage:.0%} of the required labels "
            f"(needs at least {config.min_label_coverage_for_real:.0%})"
        )

    if unsuitable:
        minimums = check.class_shortfalls(required_labels, {}, target, config)
        return StrategyDecision(
            strategy="synthetic_only",
            reasons=unsuitable,
            warnings=warnings,
            metrics=metrics,
            generation_plan=GenerationPlan(
                domain=requirements.domain,
                target_record_count=target,
                real_records_to_use=0,
                records_to_generate=target,
                missing_features=required_features,
                missing_labels=required_labels,
                class_minimums=minimums,
                required_labels=required_labels,
            ),
        )

    # Quality between the floor and "acceptable" does not change the strategy
    # (synthetic data cannot repair real records), but we tell the user.
    for name in check.dimensions_below(assessment, config.acceptable_quality):
        warnings.append(
            f"Real data {name} is below the acceptable level of {config.acceptable_quality}"
        )

    # ---------------- Step 2: is the real data enough on its own? ----------------
    gaps = []
    record_shortfall = max(0, target - available)
    if check.records_are_short(target, available, config):
        gaps.append(f"Only {available} of {target} requested records are available")
    if feature_coverage < config.min_feature_coverage:
        gaps.append(f"Missing required features: {missing_features}")
    elif missing_features:
        warnings.append(f"Some required features are missing (within tolerance): {missing_features}")
    if missing_labels:
        gaps.append(f"Required labels have no real records: {missing_labels}")
    shortfalls = check.class_shortfalls(required_labels, counts, target, config)
    present_shortfalls = {k: v for k, v in shortfalls.items() if k not in missing_labels}
    if present_shortfalls:
        gaps.append(f"Under-represented labels (records still needed): {present_shortfalls}")

    if not gaps:
        return StrategyDecision(
            strategy="real_only",
            reasons=[
                f"Real data covers the request: {available} records for {target} requested, "
                "all required features and labels present, classes balanced, quality acceptable"
            ],
            warnings=warnings,
            metrics=metrics,
            generation_plan=None,
        )

    records_to_generate = max(record_shortfall, sum(shortfalls.values()))
    return StrategyDecision(
        strategy="real_plus_synthetic",
        reasons=gaps,
        warnings=warnings,
        metrics=metrics,
        generation_plan=GenerationPlan(
            domain=requirements.domain,
            target_record_count=target,
            real_records_to_use=min(available, target),
            records_to_generate=records_to_generate,
            missing_features=missing_features,
            missing_labels=missing_labels,
            class_minimums=shortfalls,
            required_labels=required_labels,
        ),
    )