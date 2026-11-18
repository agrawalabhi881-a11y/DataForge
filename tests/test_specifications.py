import pytest
from pydantic import ValidationError

from llm_schema.specifications import DatasetSpecification
from llm_schema.specifications import SpecificationParseResult

def test_valid_dataset_specification():
    spec = DatasetSpecification(
        domain="phishing_urls",
        target_records=10000,
        fields=[
            {"name": "url", "required": True},
            {"name": "domain", "required": True},
        ],
    )

    assert spec.target_records == 10000
    assert spec.domain == "phishing_urls"
    assert len(spec.fields) == 2


def test_dataset_specification_defaults():
    spec = DatasetSpecification(
        domain="phishing_urls",
        target_records=1000,
        fields=[{"name": "url"}],
    )

    assert spec.data_preference == "real_preferred"
    assert spec.allow_synthetic_fallback is False
    assert spec.output_format == "csv"


def test_target_records_must_be_positive():
    with pytest.raises(ValidationError):
        DatasetSpecification(
            domain="phishing_urls",
            target_records=0,
            fields=[{"name": "url"}],
        )


def test_fields_cannot_be_empty():
    with pytest.raises(ValidationError):
        DatasetSpecification(
            domain="phishing_urls",
            target_records=1000,
            fields=[],
        )


def test_duplicate_field_names_are_rejected():
    with pytest.raises(ValidationError):
        DatasetSpecification(
            domain="phishing_urls",
            target_records=1000,
            fields=[
                {"name": "URL"},
                {"name": "url"},
            ],
        )

def test_incomplete_parse_result():
    result = SpecificationParseResult(
        missing_fields=["target_records"],
        clarification_questions=["How many records do you need?"],
    )

    assert result.is_complete is False
    assert "target_records" in result.missing_fields


def test_complete_parse_result():
    spec = DatasetSpecification(
        domain="phishing_urls",
        target_records=1000,
        fields=[{"name": "url"}],
    )

    result = SpecificationParseResult(specification=spec)

    assert result.is_complete is True
    assert result.missing_fields == []


def test_parse_result_rejects_missing_fields_with_specification():
    spec = DatasetSpecification(
        domain="phishing_urls",
        target_records=1000,
        fields=[{"name": "url"}],
    )

    with pytest.raises(ValidationError):
        SpecificationParseResult(
            specification=spec,
            missing_fields=["target_records"],
        )