import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from llm_schema.mapping import (
    compatibility_report,
    deterministic_mapping,
    inspect_dataset,
    llm_assisted_mapping,
    map_label,
)
from llm_schema.mapping.mapper import ColumnProfile, DatasetProfile
from llm_schema.mapping.mapper import FieldMapping, MappingResult
from llm_schema.schemas import AttackLogRecord, DatasetDomain, get_schema_for_domain


@pytest.fixture
def local_tmp_path():
    """Use the writable repository instead of the restricted Windows temp root."""
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
        yield Path(directory)


def profile(*columns):
    return DatasetProfile(path="memory.csv", format="csv", columns=list(columns))


def test_domain_registry_resolves_models_and_rejects_unknown_domain():
    assert get_schema_for_domain(DatasetDomain.ATTACK_LOGS) is AttackLogRecord
    with pytest.raises(ValueError, match="Unsupported dataset domain"):
        get_schema_for_domain("unknown")


def test_csv_inspection_reports_types_and_rejects_unsupported_format(local_tmp_path):
    tmp_path = local_tmp_path
    path = tmp_path / "input.csv"
    path.write_text(
        "url,count,optional\nhttps://example.test,1,\nhttps://sample.test,2,3\nhttps://later.test,text,4\n",
        encoding="utf-8",
    )
    inspected = inspect_dataset(path, sample_size=2)
    assert [column.name for column in inspected.columns] == ["url", "count", "optional"]
    assert inspected.sampled_row_count == inspected.row_count == 2
    assert inspected.total_row_count is None
    assert inspected.columns[1].data_type.startswith("int")
    assert inspected.columns[2].nullable is True
    with pytest.raises(ValueError, match="Unsupported"):
        inspect_dataset(tmp_path / "input.xls")


def test_json_array_inspection_is_bounded_and_reports_unknown_total(local_tmp_path):
    tmp_path = local_tmp_path
    path = tmp_path / "input.json"
    pd.DataFrame({"event_id": ["e1", "e2", "e3", "e4"], "count": [1, 2, "later", 4]}).to_json(
        path, orient="records"
    )
    inspected = inspect_dataset(path, sample_size=2)
    assert [column.name for column in inspected.columns] == ["event_id", "count"]
    assert inspected.row_count == inspected.sampled_row_count == 2
    assert inspected.total_row_count is None
    assert inspected.columns[1].data_type.startswith("int")


def test_jsonl_inspection_is_bounded_and_reports_unknown_total(local_tmp_path):
    path = local_tmp_path / "input.jsonl"
    pd.DataFrame({"event_id": ["e1", "e2", "e3"], "destination_port": [80, 443, 8080]}).to_json(
        path, orient="records", lines=True
    )
    inspected = inspect_dataset(path, sample_size=2)
    assert [column.name for column in inspected.columns] == ["event_id", "destination_port"]
    assert inspected.sampled_row_count == inspected.row_count == 2
    assert inspected.total_row_count is None


def test_parquet_inspection_is_bounded_and_uses_metadata_row_count(local_tmp_path):
    path = local_tmp_path / "input.parquet"
    pd.DataFrame({"event_id": ["e1", "e2", "e3", "e4"], "destination_port": [80, 443, 8080, 22]}).to_parquet(path)
    inspected = inspect_dataset(path, sample_size=2)
    assert [column.name for column in inspected.columns] == ["event_id", "destination_port"]
    assert inspected.sampled_row_count == inspected.row_count == 2
    assert inspected.total_row_count == 4


def test_deterministic_mapping_and_compatibility_report():
    source = profile(
        ColumnProfile(name="sample_id", data_type="object"),
        ColumnProfile(name="url", data_type="object"),
        ColumnProfile(name="mystery", data_type="object"),
    )
    mapping = deterministic_mapping(source, "phishing_urls")
    assert {item.source: item.target for item in mapping.mappings} == {"sample_id": "record_id", "url": "url"}
    report = compatibility_report(source, mapping)
    assert report.missing == []
    assert report.extra == ["mystery"]


def test_ambiguous_alias_is_reported():
    mapping = deterministic_mapping(profile(ColumnProfile(name="id", data_type="object")), "user_behavior")
    assert "id" in mapping.ambiguous
    assert mapping.ambiguous["id"] == ["event_id", "user_id"]


def test_deterministic_mapping_is_independent_of_column_order():
    columns = [
        ColumnProfile(name="id", data_type="object"),
        ColumnProfile(name="event_id", data_type="object"),
    ]
    forward = deterministic_mapping(profile(*columns), "user_behavior")
    reverse = deterministic_mapping(profile(*reversed(columns)), "user_behavior")
    assert [(item.source, item.target) for item in forward.mappings] == [
        (item.source, item.target) for item in reverse.mappings
    ]
    assert forward.ambiguous == reverse.ambiguous
    assert forward.unmapped_columns == reverse.unmapped_columns
    assert {item.source: item.target for item in forward.mappings} == {
        "event_id": "event_id",
        "id": "user_id",
    }


def test_exact_canonical_match_takes_priority_over_alias():
    mapping = deterministic_mapping(
        profile(
            ColumnProfile(name="id", data_type="object"),
            ColumnProfile(name="event_id", data_type="object"),
        ),
        "attack_logs",
    )
    assert [(item.source, item.target, item.confidence) for item in mapping.mappings] == [
        ("event_id", "event_id", 1.0)
    ]
    assert mapping.unmapped_columns == ["id"]


def test_conflicting_normalized_source_columns_are_not_assigned_twice():
    mapping = deterministic_mapping(
        profile(
            ColumnProfile(name="url", data_type="object"),
            ColumnProfile(name="u-r-l", data_type="object"),
        ),
        "phishing_urls",
    )
    assert mapping.mappings == []
    assert mapping.unmapped_columns == ["u-r-l", "url"]


def test_duplicate_normalized_alias_columns_remain_ambiguous():
    mapping = deterministic_mapping(
        profile(
            ColumnProfile(name="uid", data_type="object"),
            ColumnProfile(name="u-id", data_type="object"),
        ),
        "user_behavior",
    )
    assert mapping.mappings == []
    assert mapping.ambiguous == {"u-id": ["user_id"], "uid": ["user_id"]}


def test_compatibility_report_identifies_incompatible_source_type():
    source = profile(ColumnProfile(name="destination_port", data_type="datetime64[ns]"))
    mapping = deterministic_mapping(source, "attack_logs")
    report = compatibility_report(source, mapping)
    assert report.incompatible[0].field == "destination_port"


@pytest.mark.parametrize(
    ("source_type", "domain", "target", "status"),
    [
        ("string[python]", DatasetDomain.PHISHING_URLS, "url", "matched"),
        ("int64", DatasetDomain.ATTACK_LOGS, "destination_port", "matched"),
        ("float64", DatasetDomain.USER_BEHAVIOR, "duration", "matched"),
        ("bool", DatasetDomain.PHISHING_URLS, "https", "matched"),
        ("datetime64[ns]", DatasetDomain.ATTACK_LOGS, "timestamp", "matched"),
        ("list[int64]", DatasetDomain.VULNERABLE_CODE, "vulnerable_lines", "matched"),
        ("float64", DatasetDomain.ATTACK_LOGS, "destination_port", "incompatible"),
        ("string[python]", DatasetDomain.PHISHING_URLS, "https", "incompatible"),
        ("list[str]", DatasetDomain.VULNERABLE_CODE, "vulnerable_lines", "incompatible"),
        ("unknown-dtype", DatasetDomain.PHISHING_URLS, "url", "indeterminate"),
        ("object", DatasetDomain.VULNERABLE_CODE, "code_snippet", "indeterminate"),
        ("int64", DatasetDomain.USER_BEHAVIOR, "duration", "indeterminate"),
    ],
)
def test_compatibility_classifies_known_and_unknown_dtype_families(source_type, domain, target, status):
    source = profile(ColumnProfile(name="source", data_type=source_type))
    mapping = MappingResult(
        domain=domain,
        mappings=[FieldMapping(source="source", target=target, confidence=1.0)],
    )
    report = compatibility_report(source, mapping)
    assert len(getattr(report, status)) == 1
    assert len(report.matched) + len(report.incompatible) + len(report.indeterminate) == 1


@pytest.mark.parametrize(
    ("source", "target", "expected_reason"),
    [
        ("missing", "url", "Source column is missing"),
        ("source", "not_a_field", "Target is not a canonical field"),
    ],
)
def test_invalid_mapping_references_are_reported_and_do_not_satisfy_required_fields(
    source, target, expected_reason
):
    report = compatibility_report(
        profile(ColumnProfile(name="source", data_type="string")),
        MappingResult(
            domain=DatasetDomain.PHISHING_URLS,
            mappings=[FieldMapping(source=source, target=target, confidence=1.0)],
        ),
    )
    assert len(report.invalid_mappings) == 1
    assert expected_reason in report.invalid_mappings[0].reason
    assert {"record_id", "url"}.issubset(report.missing)


def test_missing_required_fields_are_reported_without_mappings():
    report = compatibility_report(
        profile(ColumnProfile(name="optional", data_type="string")),
        MappingResult(domain=DatasetDomain.ATTACK_LOGS, mappings=[]),
    )
    assert report.missing == ["event_id"]


def test_llm_mapping_validates_json_and_only_resolves_unknowns():
    class Client:
        def complete_with_fallback(self, prompt, response_validator=None):
            assert "sample-secret" not in prompt
            content = json.dumps({"mappings": [{"source": "weird", "target": "url", "confidence": 0.8}]})
            response_validator(content)
            return type("Response", (), {"content": content})()

    mapping = llm_assisted_mapping(
        profile(ColumnProfile(name="weird", data_type="object", samples=["sample-secret"])),
        "phishing_urls",
        Client(),
    )
    assert mapping.mappings[0].method == "llm"
    assert mapping.unmapped_columns == []


def test_llm_mapping_includes_samples_only_with_explicit_opt_in():
    class Client:
        def complete_with_fallback(self, prompt, response_validator=None):
            assert "sample-secret" in prompt
            content = json.dumps({"mappings": [{"source": "weird", "target": "url", "confidence": 0.8}]})
            response_validator(content)
            return type("Response", (), {"content": content})()

    llm_assisted_mapping(
        profile(ColumnProfile(name="weird", data_type="object", samples=["sample-secret"])),
        "phishing_urls",
        Client(),
        include_samples=True,
    )


def test_llm_mapping_rejects_invalid_structured_output():
    class Client:
        def complete_with_fallback(self, prompt, response_validator=None):
            response_validator('{"mappings":[{"source":"unknown","target":"url","confidence":1}]}')

    with pytest.raises(ValueError, match="unknown column or target"):
        llm_assisted_mapping(profile(ColumnProfile(name="weird", data_type="object")), "phishing_urls", Client())


def test_label_map_is_exact_and_preserves_original_value():
    converted = map_label("malicious", {"malicious": "phishing"})
    assert converted.source_label == "malicious"
    assert converted.canonical_label == "phishing"
    with pytest.raises(ValueError, match="No explicit"):
        map_label("MALICIOUS", {"malicious": "phishing"})


@pytest.mark.parametrize(
    ("source_label", "explicit_mapping"),
    [
        ("  malicious ", {"  malicious ": "phishing"}),
        (7, {7: "malicious"}),
        (1.5, {1.5: "suspicious"}),
        (False, {False: "benign"}),
    ],
)
def test_label_map_preserves_exact_source_value_and_type(source_label, explicit_mapping):
    converted = map_label(source_label, explicit_mapping)
    assert converted.source_label == source_label
    assert type(converted.source_label) is type(source_label)


@pytest.mark.parametrize("source_label", [None, "", "   "])
def test_label_map_rejects_null_or_blank_source_labels(source_label):
    with pytest.raises(ValueError, match="null or missing|blank"):
        map_label(source_label, {"malicious": "phishing"})


def test_label_map_requires_exact_numeric_type_and_never_guesses():
    with pytest.raises(ValueError, match="No explicit"):
        map_label(1, {True: "benign"})
    with pytest.raises(ValueError, match="No explicit"):
        map_label(1.0, {1: "benign"})


@pytest.mark.parametrize(
    ("explicit_mapping", "error", "message"),
    [
        ({}, ValueError, "at least one"),
        ({"malicious": ""}, ValueError, "non-empty strings"),
        ({"malicious": None}, ValueError, "non-empty strings"),
        ({"malicious": 1}, ValueError, "non-empty strings"),
        ({None: "phishing"}, ValueError, "non-null"),
        ({("invalid",): "phishing"}, ValueError, "non-null"),
        ([("malicious", "phishing")], TypeError, "must be a mapping"),
    ],
)
def test_label_map_rejects_invalid_mapping_definitions(explicit_mapping, error, message):
    with pytest.raises(error, match=message):
        map_label("malicious", explicit_mapping)


def test_label_map_rejects_unsupported_source_types():
    with pytest.raises(ValueError, match="must be a string, integer"):
        map_label(["malicious"], {"malicious": "phishing"})


def test_label_map_rejects_non_finite_numeric_labels():
    with pytest.raises(ValueError, match="must be finite"):
        map_label(float("nan"), {float("nan"): "unknown"})
    with pytest.raises(ValueError, match="must be finite"):
        map_label(1, {float("inf"): "unknown"})
