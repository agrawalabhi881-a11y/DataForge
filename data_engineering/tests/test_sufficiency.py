"""Sufficiency reports unmet requirements without generating data."""
from data_engineering.sufficiency.sufficiency_checker import check_dataset_sufficiency
from data_engineering.sufficiency.augmentation_requirements import calculate_augmentation_requirements


def test_sufficiency_gaps(phishing_frame):
    report = check_dataset_sufficiency(phishing_frame, domain="phishing", required_records=5000, required_features=["url", "label", "entropy"], required_labels=["benign", "suspicious", "malicious"], minimum_class_counts={"malicious": 100}, invalid_record_count=0)
    assert report["record_shortfall"] == 4997
    assert report["missing_features"] == ["entropy"]
    assert set(report["missing_or_insufficient_labels"]) == {"suspicious", "malicious"}
    assert calculate_augmentation_requirements(report)["additional_records_needed"] == 4997
