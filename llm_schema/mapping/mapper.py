"""Dataset inspection and source-to-canonical schema mapping utilities."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from llm_schema.schemas import DatasetDomain, get_schema_for_domain


class ColumnProfile(BaseModel):
    name: str
    data_type: str
    nullable: bool = True
    samples: list[str] = Field(default_factory=list)


class DatasetProfile(BaseModel):
    path: str
    format: str
    row_count: int | None = None
    columns: list[ColumnProfile]


class FieldMapping(BaseModel):
    source: str
    target: str
    method: str = "deterministic"
    confidence: float = Field(ge=0, le=1)


class MappingResult(BaseModel):
    domain: DatasetDomain
    mappings: list[FieldMapping]
    ambiguous: dict[str, list[str]] = Field(default_factory=dict)
    unmapped_columns: list[str] = Field(default_factory=list)


class FieldCompatibility(BaseModel):
    field: str
    source_column: str | None = None
    source_type: str | None = None
    canonical_type: str
    compatible: bool | None = None
    reason: str | None = None


class CompatibilityReport(BaseModel):
    matched: list[FieldCompatibility]
    missing: list[str]
    extra: list[str]
    incompatible: list[FieldCompatibility]


class LabelMapping(BaseModel):
    """Explicit label conversion; each item retains its original source value."""
    model_config = ConfigDict(extra="forbid")

    source_label: str
    canonical_label: str


LABEL_ALIASES: dict[str, set[str]] = {
    "record_id": {"id", "url_id", "sample_id", "recordid"},
    "url": {"uri", "website", "link", "full_url"},
    "domain": {"hostname", "host", "domain_name"},
    "url_length": {"url_len", "length_url"},
    "https": {"is_https", "uses_https", "ssl"},
    "event_id": {"id", "log_id", "eventid"},
    "timestamp": {"time", "datetime", "event_time"},
    "source_ip": {"src_ip", "src", "source_address"},
    "destination_ip": {"dst_ip", "dest_ip", "destination_address"},
    "source_port": {"src_port", "sport"},
    "destination_port": {"dst_port", "dest_port", "dport"},
    "protocol": {"proto"},
    "event_type": {"type", "event", "action"},
    "attack_stage": {"stage", "kill_chain_stage"},
    "code_id": {"id", "sample_id", "snippet_id"},
    "code_snippet": {"code", "source_code", "snippet"},
    "programming_language": {"language", "lang"},
    "vulnerability_type": {"vulnerability", "weakness", "cwe_name"},
    "cwe_id": {"cwe", "weakness_id"},
    "vulnerable_lines": {"line_numbers", "vulnerable_line"},
    "user_id": {"uid", "account_id", "id"},
    "activity_type": {"activity", "action_type"},
    "device": {"device_type", "client_device"},
    "resource": {"resource_name", "object"},
    "duration": {"duration_seconds", "elapsed_time"},
    "anomaly_score": {"score", "risk_score"},
    "label": {"class", "target", "class_label", "category"},
}


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.casefold())


def inspect_dataset(path: str | Path, sample_size: int = 100) -> DatasetProfile:
    """Inspect CSV, JSON/JSONL, or Parquet column names, types, and sample values."""
    file_path = Path(path)
    suffix = file_path.suffix.casefold()
    if sample_size < 1:
        raise ValueError("sample_size must be positive")
    if suffix == ".csv":
        frame = pd.read_csv(file_path, nrows=sample_size)
    elif suffix in {".json", ".jsonl", ".ndjson"}:
        try:
            frame = pd.read_json(file_path, lines=suffix in {".jsonl", ".ndjson"})
        except ValueError:
            frame = pd.read_json(file_path, lines=True)
        frame = frame.head(sample_size)
    elif suffix in {".parquet", ".pq"}:
        frame = pd.read_parquet(file_path).head(sample_size)
    else:
        raise ValueError(f"Unsupported dataset format: {suffix or '(no extension)'}")
    profiles = []
    for name in frame.columns:
        series = frame[name]
        values = [str(value)[:160] for value in series.dropna().head(3).tolist()]
        profiles.append(ColumnProfile(name=str(name), data_type=str(series.dtype), nullable=bool(series.isna().any()), samples=values))
    return DatasetProfile(path=str(file_path), format=suffix.lstrip("."), row_count=len(frame), columns=profiles)


def deterministic_mapping(profile: DatasetProfile, domain: DatasetDomain | str) -> MappingResult:
    model = get_schema_for_domain(domain)
    fields = set(model.model_fields)
    normalized_fields: dict[str, list[str]] = {}
    for field in fields:
        normalized_fields.setdefault(_normalize(field), []).append(field)
        for alias in LABEL_ALIASES.get(field, set()):
            normalized_fields.setdefault(_normalize(alias), []).append(field)
    mappings, ambiguous, unmapped = [], {}, []
    used_targets: set[str] = set()
    for column in profile.columns:
        targets = list(dict.fromkeys(normalized_fields.get(_normalize(column.name), [])))
        targets = [target for target in targets if target not in used_targets]
        if len(targets) == 1:
            exact = _normalize(column.name) == _normalize(targets[0])
            mappings.append(FieldMapping(source=column.name, target=targets[0], confidence=1.0 if exact else 0.9))
            used_targets.add(targets[0])
        elif len(targets) > 1:
            ambiguous[column.name] = targets
        else:
            unmapped.append(column.name)
    return MappingResult(domain=domain, mappings=mappings, ambiguous=ambiguous, unmapped_columns=unmapped)


def llm_assisted_mapping(profile: DatasetProfile, domain: DatasetDomain | str, client: Any) -> MappingResult:
    """Use the configured LLM client only for unresolved columns, validating JSON strictly."""
    result = deterministic_mapping(profile, domain)
    if not result.unmapped_columns and not result.ambiguous:
        return result
    model = get_schema_for_domain(domain)
    candidates = sorted(model.model_fields)
    unresolved = result.unmapped_columns + list(result.ambiguous)
    prompt = (
        "Map dataset columns to canonical fields. Return only JSON as "
        '{"mappings":[{"source":"...","target":"...","confidence":0.0}]}. '
        "Use only candidate targets; omit columns with no reliable match. Never infer from labels alone.\n"
        f"Candidates: {json.dumps(candidates)}\nColumns: {json.dumps([c.model_dump() for c in profile.columns if c.name in unresolved])}"
    )

    def validate(content: str) -> None:
        try:
            payload = json.loads(content)
            if not isinstance(payload, dict) or set(payload) != {"mappings"} or not isinstance(payload["mappings"], list):
                raise ValueError("Expected a mappings object")
            for item in payload["mappings"]:
                if set(item) != {"source", "target", "confidence"} or item["source"] not in unresolved or item["target"] not in candidates:
                    raise ValueError("Mapping contains an unknown column or target")
                FieldMapping(**item, method="llm")
        except (json.JSONDecodeError, TypeError, ValidationError) as error:
            raise ValueError("Invalid structured mapping response") from error

    response = client.complete_with_fallback(prompt, response_validator=validate)
    payload = json.loads(response.content)
    existing = {mapping.source for mapping in result.mappings}
    used_targets = {mapping.target for mapping in result.mappings}
    for item in payload["mappings"]:
        if item["source"] not in existing and item["target"] not in used_targets:
            result.mappings.append(FieldMapping(**item, method="llm"))
            existing.add(item["source"])
            used_targets.add(item["target"])
    result.unmapped_columns = [column for column in result.unmapped_columns if column not in existing]
    result.ambiguous = {key: value for key, value in result.ambiguous.items() if key not in existing}
    return result


def _canonical_type(annotation: Any) -> str:
    return str(annotation).replace("<class '", "").replace("'>", "")


def _types_compatible(source: str, target: str) -> bool:
    source, target = source.casefold(), target.casefold()
    if any(token in target for token in ("str", "string")):
        return any(token in source for token in ("object", "string", "str", "category"))
    if "bool" in target:
        return "bool" in source or "object" in source
    if "int" in target:
        return any(token in source for token in ("int", "object", "string"))
    if any(token in target for token in ("float", "decimal")):
        return any(token in source for token in ("float", "int", "object", "string"))
    if "datetime" in target:
        return any(token in source for token in ("datetime", "object", "string"))
    return True


def compatibility_report(profile: DatasetProfile, mapping: MappingResult) -> CompatibilityReport:
    model = get_schema_for_domain(mapping.domain)
    by_source = {column.name: column for column in profile.columns}
    by_target = {item.target: item for item in mapping.mappings}
    required = {name for name, field in model.model_fields.items() if field.is_required()}
    matched, incompatible = [], []
    for target, field_mapping in by_target.items():
        source_column = by_source[field_mapping.source]
        canonical = _canonical_type(model.model_fields[target].annotation)
        compatible = _types_compatible(source_column.data_type, canonical)
        item = FieldCompatibility(field=target, source_column=field_mapping.source, source_type=source_column.data_type, canonical_type=canonical, compatible=compatible, reason=None if compatible else "Source type may not be converted safely")
        (matched if compatible else incompatible).append(item)
    missing = sorted(required - set(by_target))
    extra = sorted(mapping.unmapped_columns + list(mapping.ambiguous))
    return CompatibilityReport(matched=matched, missing=missing, extra=extra, incompatible=incompatible)


def map_label(source_label: str, explicit_mapping: dict[str, str]) -> LabelMapping:
    """Apply a caller-supplied exact label map while preserving the source label."""
    if source_label not in explicit_mapping:
        raise ValueError(f"No explicit canonical mapping provided for label {source_label!r}")
    return LabelMapping(source_label=source_label, canonical_label=explicit_mapping[source_label])
