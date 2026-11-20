"""DataForge - Data Engineering: deterministic content fingerprints and version records."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


def dataframe_fingerprint(dataframe: pd.DataFrame) -> str:
    """Hash ordered rows, column names, dtypes and index for reproducible comparisons.

    Requires values serializable by pandas' JSON encoder. A fingerprint is not a
    cryptographic proof of source authenticity and does not replace source checksums.
    """
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a pandas DataFrame")
    if not dataframe.columns.is_unique:
        raise ValueError("DataFrame column names must be unique")
    metadata = json.dumps({"columns": list(map(str, dataframe.columns)),
                           "dtypes": [str(t) for t in dataframe.dtypes]},
                          sort_keys=True, separators=(",", ":"))
    content = dataframe.to_json(orient="split", date_format="iso", date_unit="ns",
                                index=True, force_ascii=False)
    return sha256((metadata + "\n" + content).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DatasetVersion:
    dataset_id: str
    version: str
    content_sha256: str
    created_at_utc: str
    schema_version: str | None
    parent_version: str | None
    processing_configuration: dict[str, Any]
    lineage_fingerprint: str | None
    quality_report_reference: str | None
    record_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_dataset_version(
    dataframe: pd.DataFrame, *, dataset_id: str, version: str,
    schema_version: str | None = None, parent_version: str | None = None,
    processing_configuration: Mapping[str, Any] | None = None,
    lineage_fingerprint: str | None = None,
    quality_report_reference: str | None = None,
) -> DatasetVersion:
    if not isinstance(dataset_id, str) or not dataset_id.strip():
        raise ValueError("dataset_id must be a non-empty string")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("version must be a non-empty string")
    if processing_configuration is not None and not isinstance(processing_configuration, Mapping):
        raise TypeError("processing_configuration must be a mapping")
    config = json.loads(json.dumps(dict(processing_configuration or {}), allow_nan=False))
    return DatasetVersion(
        dataset_id=dataset_id, version=version,
        content_sha256=dataframe_fingerprint(dataframe),
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        schema_version=schema_version, parent_version=parent_version,
        processing_configuration=config, lineage_fingerprint=lineage_fingerprint,
        quality_report_reference=quality_report_reference, record_count=len(dataframe),
    )


def save_version_manifest(manifest: DatasetVersion, path: str | Path,
                          *, overwrite: bool = False) -> Path:
    if not isinstance(manifest, DatasetVersion):
        raise TypeError("manifest must be a DatasetVersion")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w" if overwrite else "x", encoding="utf-8") as handle:
        json.dump(manifest.to_dict(), handle, indent=2, ensure_ascii=False)
    return target


def verify_dataset_version(dataframe: pd.DataFrame, manifest: DatasetVersion) -> bool:
    if not isinstance(manifest, DatasetVersion):
        raise TypeError("manifest must be a DatasetVersion")
    return (len(dataframe) == manifest.record_count and
            dataframe_fingerprint(dataframe) == manifest.content_sha256)
