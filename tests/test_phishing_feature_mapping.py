from pydantic import ValidationError
import pytest

from llm_schema.mapping import deterministic_mapping
from llm_schema.mapping.mapper import ColumnProfile, DatasetProfile
from llm_schema.schemas import PhishingURLRecord


def _profile(*names_and_types):
    return DatasetProfile(
        path="memory.csv",
        format="csv",
        columns=[
            ColumnProfile(name=name, data_type=data_type)
            for name, data_type in names_and_types
        ],
    )


def test_terminal_demo_phishing_fields_map_to_distinct_canonical_fields():
    source = _profile(
        ("URL", "string"),
        ("domain", "string"),
        ("URL length", "int64"),
        ("HTTPS presence", "bool"),
        ("IP address presence", "bool"),
        ("number of dots", "int64"),
        ("label", "string"),
    )

    mapping = deterministic_mapping(source, "phishing_urls")

    assert {item.source: item.target for item in mapping.mappings} == {
        "URL": "url",
        "domain": "domain",
        "URL length": "url_length",
        "HTTPS presence": "https",
        "IP address presence": "has_ip_address",
        "number of dots": "dot_count",
        "label": "label",
    }
    assert mapping.unmapped_columns == []
    assert mapping.ambiguous == {}


def test_phishing_schema_accepts_ip_presence_and_dot_count():
    record = PhishingURLRecord(
        record_id="p-001",
        url="https://example.test/path",
        https=True,
        has_ip_address=False,
        dot_count=2,
    )

    assert record.has_ip_address is False
    assert record.dot_count == 2


def test_phishing_schema_rejects_negative_dot_count():
    with pytest.raises(ValidationError):
        PhishingURLRecord(
            record_id="p-002",
            url="https://example.test",
            dot_count=-1,
        )
