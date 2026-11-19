from app.adaptive_engine.decision_config import DecisionConfig
from app.adaptive_engine.strategy_selector import select_strategy
from app.schemas.strategy import RealDataAssessment, Requirements, SourceEligibility

GOOD_SOURCE = [SourceEligibility(source_id=1, license_status="verified_open", acquired=True)]


def reqs(count=50000, features=None, labels=None, domain="phishing"):
    return Requirements(
        domain=domain,
        record_count=count,
        required_features=features if features is not None else [f"f{i}" for i in range(20)],
        required_labels=labels if labels is not None else ["benign", "suspicious", "malicious"],
    )


def real(records=50000, features=None, labels=None, q=0.95, relevance=0.9):
    return RealDataAssessment(
        available_record_count=records,
        available_features=features if features is not None else [f"f{i}" for i in range(20)],
        label_counts=labels if labels is not None else {"benign": 20000, "suspicious": 15000, "malicious": 15000},
        completeness=q, validity=q, consistency=q, relevance=relevance,
    )


def test_real_only_when_everything_is_covered():
    d = select_strategy(reqs(), real(), GOOD_SOURCE)
    assert d.strategy == "real_only"
    assert d.generation_plan is None


def test_assignment_example_real_plus_synthetic():
    a = real(records=30000, features=[f"f{i}" for i in range(18)],
             labels={"benign": 20000, "suspicious": 9000, "malicious": 1000})
    d = select_strategy(reqs(), a, GOOD_SOURCE)
    assert d.strategy == "real_plus_synthetic"
    plan = d.generation_plan
    assert plan.records_to_generate == 20000
    assert plan.missing_features == ["f18", "f19"]
    assert "malicious" in plan.class_minimums
    assert plan.real_records_to_use == 30000


def test_no_sources_is_synthetic_only():
    d = select_strategy(reqs(), real(), [])
    assert d.strategy == "synthetic_only"
    assert d.generation_plan.records_to_generate == 50000
    assert d.generation_plan.real_records_to_use == 0


def test_unverified_license_is_never_used():
    src = [SourceEligibility(source_id=1, license_status="unverified", acquired=True)]
    d = select_strategy(reqs(), real(), src)
    assert d.strategy == "synthetic_only"
    assert any("license" in w for w in d.warnings)


def test_restricted_license_is_never_used():
    src = [SourceEligibility(source_id=1, license_status="restricted", acquired=True)]
    assert select_strategy(reqs(), real(), src).strategy == "synthetic_only"


def test_one_good_source_among_bad_is_enough():
    src = GOOD_SOURCE + [SourceEligibility(source_id=2, license_status="unverified", acquired=True)]
    d = select_strategy(reqs(), real(), src)
    assert d.strategy == "real_only"
    assert d.metrics["eligible_sources"] == 1


def test_not_acquired_or_no_access():
    src = [SourceEligibility(source_id=1, license_status="verified_open", acquired=False)]
    assert select_strategy(reqs(), real(), src).strategy == "synthetic_only"
    src = [SourceEligibility(source_id=1, license_status="verified_open", acquired=True, access_ok=False)]
    assert select_strategy(reqs(), real(), src).strategy == "synthetic_only"


def test_low_relevance():
    assert select_strategy(reqs(), real(relevance=0.1), GOOD_SOURCE).strategy == "synthetic_only"


def test_quality_below_floor_is_synthetic_only():
    assert select_strategy(reqs(), real(q=0.3), GOOD_SOURCE).strategy == "synthetic_only"


def test_quality_between_floor_and_acceptable_only_warns():
    d = select_strategy(reqs(), real(q=0.65), GOOD_SOURCE)
    assert d.strategy == "real_only"
    assert any("acceptable" in w for w in d.warnings)


def test_zero_records():
    assert select_strategy(reqs(), real(records=0, labels={}), GOOD_SOURCE).strategy == "synthetic_only"


def test_low_feature_coverage_is_synthetic_only():
    d = select_strategy(reqs(), real(features=["f0", "f1", "f2"]), GOOD_SOURCE)
    assert d.strategy == "synthetic_only"


def test_no_required_label_present_is_synthetic_only():
    d = select_strategy(reqs(), real(labels={"other": 50000}), GOOD_SOURCE)
    assert d.strategy == "synthetic_only"


def test_one_missing_label_is_real_plus_synthetic():
    d = select_strategy(reqs(), real(labels={"benign": 25000, "suspicious": 25000}), GOOD_SOURCE)
    assert d.strategy == "real_plus_synthetic"
    assert d.generation_plan.missing_labels == ["malicious"]


def test_same_record_count_different_outcome_because_of_imbalance():
    balanced = select_strategy(reqs(), real(), GOOD_SOURCE)
    skewed = select_strategy(
        reqs(), real(labels={"benign": 49000, "suspicious": 500, "malicious": 500}), GOOD_SOURCE)
    assert balanced.strategy == "real_only"
    assert skewed.strategy == "real_plus_synthetic"
    assert set(skewed.generation_plan.class_minimums) == {"suspicious", "malicious"}


def test_only_features_missing_generates_zero_new_records():
    d = select_strategy(reqs(), real(features=[f"f{i}" for i in range(19)]), GOOD_SOURCE)
    assert d.strategy == "real_plus_synthetic"
    assert d.generation_plan.records_to_generate == 0
    assert d.generation_plan.missing_features == ["f19"]


def test_names_are_case_insensitive():
    a = real(features=[f"F{i}" for i in range(20)],
             labels={"BENIGN": 20000, "Suspicious": 15000, "MALICIOUS": 15000})
    assert select_strategy(reqs(), a, GOOD_SOURCE).strategy == "real_only"


def test_single_label_has_no_balance_rule():
    d = select_strategy(reqs(labels=["malicious"]), real(labels={"malicious": 50000}), GOOD_SOURCE)
    assert d.strategy == "real_only"


def test_many_labels_do_not_make_it_impossible():
    labels = [f"c{i}" for i in range(20)]
    d = select_strategy(reqs(labels=labels), real(labels={l: 2500 for l in labels}), GOOD_SOURCE)
    assert d.strategy == "real_only"


def test_config_can_be_changed():
    a = real(records=30000, labels={"benign": 10000, "suspicious": 10000, "malicious": 10000})
    assert select_strategy(reqs(), a, GOOD_SOURCE).strategy == "real_plus_synthetic"
    lenient = DecisionConfig(min_record_ratio=0.5)
    assert select_strategy(reqs(), a, GOOD_SOURCE, lenient).strategy == "real_only"
    open_all = DecisionConfig(allowed_license_statuses=("verified_open", "unverified"))
    src = [SourceEligibility(source_id=1, license_status="unverified", acquired=True)]
    assert select_strategy(reqs(), real(), src, open_all).strategy == "real_only"