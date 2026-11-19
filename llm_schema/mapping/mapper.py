"""Dataset inspection and source-to-canonical schema mapping utilities."""
from __future__ import annotations

import json
import io
import itertools
import math
import re
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    ValidationError,
)

from llm_schema.schemas import DatasetDomain, get_schema_for_domain


class ColumnProfile(BaseModel):
    name: str
    data_type: str
    nullable: bool = True
    samples: list[str] = Field(default_factory=list)


class DatasetProfile(BaseModel):
    path: str
    format: str
    # Legacy field: number of rows inspected, never the dataset total.
    row_count: int | None = None
    columns: list[ColumnProfile]
    total_row_count: int | None = None
    sampled_row_count: int | None = None


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


class MappingIssue(BaseModel):
    source: str
    target: str
    reason: str


class CompatibilityReport(BaseModel):
    matched: list[FieldCompatibility]
    missing: list[str]
    extra: list[str]
    incompatible: list[FieldCompatibility]
    indeterminate: list[FieldCompatibility] = Field(default_factory=list)
    invalid_mappings: list[MappingIssue] = Field(default_factory=list)


class LabelMapping(BaseModel):
    """Explicit label conversion; each item retains its original source value."""
    model_config = ConfigDict(extra="forbid")

    source_label: StrictStr | StrictInt | StrictFloat | StrictBool
    canonical_label: StrictStr


LABEL_ALIASES: dict[str, set[str]] = {
    "record_id": {"id", "url_id", "sample_id", "recordid"},
    "url": {"uri", "website", "link", "full_url"},
    "domain": {"hostname", "host", "domain_name"},
    "url_length": {"url_len", "length_url"},
    "https": {"is_https", "uses_https", "ssl", "https_presence", "has_https"},
    "has_ip_address": {"ip_address_presence", "ip_address_present", "ip_present", "contains_ip_address", "has_ip"},
    "dot_count": {"number_of_dots", "num_dots", "dots_count", "dotcount"},
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


def _iter_json_array(stream: io.TextIOBase) -> Iterator[Any]:
    """Yield top-level JSON array items incrementally using the stdlib decoder."""
    decoder = json.JSONDecoder()
    buffer = stream.read(65536)
    position = 0
    eof = not buffer

    def refill() -> None:
        nonlocal buffer, position, eof
        remaining = buffer[position:]
        chunk = stream.read(65536)
        buffer = remaining + chunk
        position = 0
        eof = not chunk

    def skip_whitespace() -> None:
        nonlocal position
        while True:
            while position < len(buffer) and buffer[position].isspace():
                position += 1
            if position < len(buffer) or eof:
                return
            refill()

    skip_whitespace()
    if position >= len(buffer) or buffer[position] != "[":
        raise ValueError("Expected a JSON record array")
    position += 1
    first = True

    while True:
        skip_whitespace()
        if position >= len(buffer):
            raise ValueError("Unterminated JSON record array")
        if buffer[position] == "]":
            return
        if not first:
            if buffer[position] != ",":
                raise ValueError("Expected a comma between JSON records")
            position += 1
            skip_whitespace()
        while True:
            try:
                item, end = decoder.raw_decode(buffer, position)
                position = end
                break
            except json.JSONDecodeError:
                if eof:
                    raise
                refill()
        yield item
        first = False


def _read_json_array_sample(path: Path, sample_size: int) -> pd.DataFrame:
    with path.open("r", encoding="utf-8") as stream:
        records = list(itertools.islice(_iter_json_array(stream), sample_size))
    return pd.DataFrame(records)


def inspect_dataset(path: str | Path, sample_size: int = 100) -> DatasetProfile:
    """Inspect a bounded sample; types and nullability describe inspected rows only."""
    file_path = Path(path)
    suffix = file_path.suffix.casefold()
    if sample_size < 1:
        raise ValueError("sample_size must be positive")
    total_row_count = None
    if suffix == ".csv":
        frame = pd.read_csv(file_path, nrows=sample_size)
    elif suffix in {".jsonl", ".ndjson"}:
        chunks = pd.read_json(file_path, lines=True, chunksize=sample_size)
        frame = next(chunks, pd.DataFrame())
    elif suffix == ".json":
        with file_path.open("r", encoding="utf-8") as stream:
            while True:
                first_character = stream.read(1)
                if not first_character:
                    raise ValueError("JSON dataset is empty")
                if not first_character.isspace():
                    break
        if first_character == "[":
            frame = _read_json_array_sample(file_path, sample_size)
        else:
            # Preserve support for pandas' object-oriented JSON formats.
            frame = pd.read_json(file_path).head(sample_size)
    elif suffix in {".parquet", ".pq"}:
        import pyarrow.parquet as parquet

        parquet_file = parquet.ParquetFile(file_path)
        metadata = parquet_file.metadata
        total_row_count = metadata.num_rows if metadata is not None else None
        batch = next(parquet_file.iter_batches(batch_size=sample_size), None)
        frame = batch.to_pandas() if batch is not None else pd.DataFrame(columns=parquet_file.schema_arrow.names)
    else:
        raise ValueError(f"Unsupported dataset format: {suffix or '(no extension)'}")
    profiles = []
    for name in frame.columns:
        series = frame[name]
        values = [str(value)[:160] for value in series.dropna().head(3).tolist()]
        profiles.append(ColumnProfile(name=str(name), data_type=str(series.dtype), nullable=bool(series.isna().any()), samples=values))
    sampled_row_count = len(frame)
    return DatasetProfile(
        path=str(file_path),
        format=suffix.lstrip("."),
        row_count=sampled_row_count,
        total_row_count=total_row_count,
        sampled_row_count=sampled_row_count,
        columns=profiles,
    )


def deterministic_mapping(profile: DatasetProfile, domain: DatasetDomain | str) -> MappingResult:
    model = get_schema_for_domain(domain)
    fields = list(model.model_fields)
    canonical_by_name = {_normalize(field): field for field in fields}
    aliases_by_name: dict[str, list[str]] = {}
    for field in fields:
        for alias in sorted(LABEL_ALIASES.get(field, set())):
            aliases_by_name.setdefault(_normalize(alias), []).append(field)
    for targets in aliases_by_name.values():
        targets.sort()

    columns_by_name: dict[str, list[ColumnProfile]] = {}
    for column in profile.columns:
        columns_by_name.setdefault(_normalize(column.name), []).append(column)

    mappings: list[FieldMapping] = []
    ambiguous: dict[str, list[str]] = {}
    unmapped: list[str] = []
    reserved_targets = {
        canonical_by_name[name]
        for name in columns_by_name
        if name in canonical_by_name
    }
    assigned_targets: set[str] = set()

    # Canonical names claim their targets before any aliases, independent of
    # source column ordering. Normalization collisions are left unresolved.
    for normalized_name in sorted(columns_by_name):
        columns = sorted(columns_by_name[normalized_name], key=lambda item: item.name)
        target = canonical_by_name.get(normalized_name)
        if target is None:
            continue
        if len(columns) != 1:
            unmapped.extend(column.name for column in columns)
            continue
        mappings.append(FieldMapping(source=columns[0].name, target=target, confidence=1.0))
        assigned_targets.add(target)

    alias_claims: dict[str, list[tuple[ColumnProfile, list[str]]]] = {}
    for normalized_name in sorted(columns_by_name):
        if normalized_name in canonical_by_name:
            continue
        columns = sorted(columns_by_name[normalized_name], key=lambda item: item.name)
        targets = [target for target in aliases_by_name.get(normalized_name, []) if target not in reserved_targets]
        targets = sorted(set(targets))
        if not targets:
            unmapped.extend(column.name for column in columns)
            continue
        if len(columns) > 1:
            for column in columns:
                ambiguous[column.name] = targets
            continue
        alias_claims.setdefault(targets[0] if len(targets) == 1 else "", []).append((columns[0], targets))

    # A canonical target claimed by multiple aliases remains ambiguous instead
    # of being awarded to whichever source column happened to appear first.
    claims_by_target: dict[str, list[ColumnProfile]] = {}
    for claimed_target, claims in alias_claims.items():
        if claimed_target:
            claims_by_target.setdefault(claimed_target, []).extend(column for column, _ in claims)
        else:
            for column, targets in claims:
                ambiguous[column.name] = targets

    for target in sorted(claims_by_target):
        columns = sorted(claims_by_target[target], key=lambda item: item.name)
        if target in assigned_targets or len(columns) > 1:
            for column in columns:
                ambiguous[column.name] = [target]
            continue
        column = columns[0]
        mappings.append(FieldMapping(source=column.name, target=target, confidence=0.9))
        assigned_targets.add(target)

    mappings.sort(key=lambda item: (_normalize(item.source), item.source, item.target))
    ambiguous = dict(sorted(ambiguous.items()))
    unmapped.sort()
    return MappingResult(domain=domain, mappings=mappings, ambiguous=ambiguous, unmapped_columns=unmapped)


def llm_assisted_mapping(
    profile: DatasetProfile,
    domain: DatasetDomain | str,
    client: Any,
    *,
    include_samples: bool = False,
) -> MappingResult:
    """Resolve remaining columns; sample values are sent only with explicit opt-in."""
    result = deterministic_mapping(profile, domain)
    if not result.unmapped_columns and not result.ambiguous:
        return result
    model = get_schema_for_domain(domain)
    candidates = sorted(model.model_fields)
    unresolved = result.unmapped_columns + list(result.ambiguous)
    columns = [
        column.model_dump() if include_samples else column.model_dump(exclude={"samples"})
        for column in profile.columns
        if column.name in unresolved
    ]
    prompt = (
        "Map dataset columns to canonical fields. Return only JSON as "
        '{"mappings":[{"source":"...","target":"...","confidence":0.0}]}. '
        "Use only candidate targets; omit columns with no reliable match. Never infer from labels alone.\n"
        f"Candidates: {json.dumps(candidates)}\nColumns: {json.dumps(columns)}"
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


def _dtype_family(data_type: str) -> tuple[str, str | None] | None:
    """Classify known pandas/Arrow dtype spellings; unknowns stay indeterminate."""
    normalized = data_type.casefold().replace(" ", "")
    if normalized.startswith(("list[", "list<")):
        if normalized.startswith("list[") and normalized.endswith("]"):
            item_type = normalized[5:-1]
        elif "item:" in normalized and normalized.endswith(">"):
            item_type = normalized.split("item:", 1)[1][:-1]
        else:
            return "collection", None
        item_family = _dtype_family(item_type)
        return "collection", item_family[0] if item_family else None
    if normalized in {"str", "string", "string[python]", "string[pyarrow]"}:
        return "string", None
    if normalized in {"bool", "boolean"}:
        return "boolean", None
    if re.fullmatch(r"u?int(?:8|16|32|64|128)?", normalized):
        return "integer", None
    if re.fullmatch(r"(?:float|double)(?:16|32|64|128)?", normalized):
        return "floating", None
    if normalized.startswith(("datetime64[", "timestamp[")) or normalized in {"datetime", "datetime.datetime"}:
        return "datetime", None
    return None


def _types_compatible(source: str, target: str) -> bool | None:
    """Compare known dtype families only; this does not validate row values."""
    source_family = _dtype_family(source)
    target_type = target.casefold().replace(" | none", "").strip()
    if target_type.startswith("list[") and target_type.endswith("]"):
        target_item = _dtype_family(target_type[5:-1])
        target_family = ("collection", target_item[0] if target_item else None)
    else:
        target_family = _dtype_family(target_type)
    if source_family is None or target_family is None:
        return None
    if source_family[0] == "collection" and target_family[0] == "collection":
        if source_family[1] is None or target_family[1] is None:
            return None
        return source_family[1] == target_family[1]
    if source_family[0] == target_family[0]:
        return True
    if source_family[0] == "integer" and target_family[0] == "floating":
        # Large integers may lose precision when converted to floating point.
        return None
    return False


def compatibility_report(profile: DatasetProfile, mapping: MappingResult) -> CompatibilityReport:
    """Compare mapped dtype families without scanning dataset values."""
    model = get_schema_for_domain(mapping.domain)
    source_counts: dict[str, int] = {}
    by_source: dict[str, ColumnProfile] = {}
    for column in profile.columns:
        source_counts[column.name] = source_counts.get(column.name, 0) + 1
        by_source[column.name] = column

    source_mapping_counts: dict[str, int] = {}
    target_mapping_counts: dict[str, int] = {}
    for item in mapping.mappings:
        source_mapping_counts[item.source] = source_mapping_counts.get(item.source, 0) + 1
        target_mapping_counts[item.target] = target_mapping_counts.get(item.target, 0) + 1

    canonical_fields = set(model.model_fields)
    invalid_mappings: list[MappingIssue] = []
    valid_mappings: list[FieldMapping] = []
    for item in mapping.mappings:
        reasons = []
        if source_counts.get(item.source, 0) != 1:
            reasons.append("Source column is missing or not unique")
        if item.target not in canonical_fields:
            reasons.append("Target is not a canonical field for this domain")
        if source_mapping_counts[item.source] > 1:
            reasons.append("Source column is mapped more than once")
        if target_mapping_counts[item.target] > 1:
            reasons.append("Canonical target is mapped more than once")
        if reasons:
            invalid_mappings.append(MappingIssue(source=item.source, target=item.target, reason="; ".join(reasons)))
        else:
            valid_mappings.append(item)

    required = {name for name, field in model.model_fields.items() if field.is_required()}
    matched, incompatible, indeterminate = [], [], []
    valid_targets: set[str] = set()
    for field_mapping in valid_mappings:
        target = field_mapping.target
        source_column = by_source[field_mapping.source]
        canonical = _canonical_type(model.model_fields[target].annotation)
        compatible = _types_compatible(source_column.data_type, canonical)
        reason = (
            None if compatible is True else
            "Known source and canonical dtype families are incompatible" if compatible is False else
            "Source or canonical dtype family is unknown; values were not scanned"
        )
        item = FieldCompatibility(field=target, source_column=field_mapping.source, source_type=source_column.data_type, canonical_type=canonical, compatible=compatible, reason=reason)
        if compatible is True:
            matched.append(item)
        elif compatible is False:
            incompatible.append(item)
        else:
            indeterminate.append(item)
        valid_targets.add(target)
    missing = sorted(required - valid_targets)
    extra = sorted(mapping.unmapped_columns + list(mapping.ambiguous))
    return CompatibilityReport(
        matched=matched,
        missing=missing,
        extra=extra,
        incompatible=incompatible,
        indeterminate=indeterminate,
        invalid_mappings=invalid_mappings,
    )


def map_label(
    source_label: str | int | float | bool | None,
    explicit_mapping: Mapping[str | int | float | bool | None, str],
) -> LabelMapping:
    """Apply an exact caller-supplied label map; null and unmapped labels are errors."""
    if source_label is None:
        raise ValueError("Source label is null or missing")
    if type(source_label) not in {str, int, float, bool}:
        raise ValueError("Source label must be a string, integer, finite float, or boolean")
    if isinstance(source_label, str) and not source_label.strip():
        raise ValueError("Source label is blank")
    if isinstance(source_label, float) and not math.isfinite(source_label):
        raise ValueError("Source label float must be finite")
    if not isinstance(explicit_mapping, Mapping):
        raise TypeError("explicit_mapping must be a mapping")
    if not explicit_mapping:
        raise ValueError("explicit_mapping must contain at least one entry")

    for key, value in explicit_mapping.items():
        if key is None or type(key) not in {str, int, float, bool}:
            raise ValueError(
                "Mapping keys must be non-null string, integer, finite float, or boolean labels"
            )
        if isinstance(key, str) and not key.strip():
            raise ValueError("Mapping keys cannot be blank")
        if isinstance(key, float) and not math.isfinite(key):
            raise ValueError("Mapping float keys must be finite")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Canonical label values must be non-empty strings")

    for key, value in explicit_mapping.items():
        if type(key) is type(source_label) and key == source_label:
            return LabelMapping(source_label=source_label, canonical_label=value)
    raise ValueError(f"No explicit canonical mapping provided for label {source_label!r}")
