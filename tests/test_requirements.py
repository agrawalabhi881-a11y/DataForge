from llm_schema.specifications.partial import PartialDatasetRequirements
from llm_schema.specifications.requirements import find_missing_requirements


def test_no_missing_requirements():
    requirements = PartialDatasetRequirements(
        domain="phishing_urls",
        target_records=1000,
        fields=[{"name": "url"}],
    )

    assert find_missing_requirements(requirements) == []


def test_missing_target_records():
    requirements = PartialDatasetRequirements(
        domain="phishing_urls",
        fields=[{"name": "url"}],
    )

    assert find_missing_requirements(requirements) == ["target_records"]


def test_all_required_information_missing():
    requirements = PartialDatasetRequirements()

    assert find_missing_requirements(requirements) == [
        "domain",
        "target_records",
        "fields",
    ]