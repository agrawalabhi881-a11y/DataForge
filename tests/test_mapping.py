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
    path.write_text("url,label\nhttps://example.test,1\n", encoding="utf-8")
    inspected = inspect_dataset(path)
    assert [column.name for column in inspected.columns] == ["url", "label"]
    assert inspected.columns[0].data_type in {"object", "str"}
    with pytest.raises(ValueError, match="Unsupported"):
        inspect_dataset(tmp_path / "input.xls")


@pytest.mark.parametrize("suffix", ["json", "jsonl", "parquet"])
def test_inspection_supports_json_and_parquet(local_tmp_path, suffix):
    tmp_path = local_tmp_path
    frame = pd.DataFrame({"event_id": ["e1"], "destination_port": [443]})
    path = tmp_path / f"input.{suffix}"
    if suffix == "json":
        frame.to_json(path, orient="records")
    elif suffix == "jsonl":
        frame.to_json(path, orient="records", lines=True)
    else:
        frame.to_parquet(path)
    inspected = inspect_dataset(path)
    assert [column.name for column in inspected.columns] == ["event_id", "destination_port"]


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


def test_compatibility_report_identifies_incompatible_source_type():
    source = profile(ColumnProfile(name="destination_port", data_type="datetime64[ns]"))
    mapping = deterministic_mapping(source, "attack_logs")
    report = compatibility_report(source, mapping)
    assert report.incompatible[0].field == "destination_port"


def test_llm_mapping_validates_json_and_only_resolves_unknowns():
    class Client:
        def complete_with_fallback(self, prompt, response_validator=None):
            content = json.dumps({"mappings": [{"source": "weird", "target": "url", "confidence": 0.8}]})
            response_validator(content)
            return type("Response", (), {"content": content})()

    mapping = llm_assisted_mapping(profile(ColumnProfile(name="weird", data_type="object")), "phishing_urls", Client())
    assert mapping.mappings[0].method == "llm"
    assert mapping.unmapped_columns == []


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
