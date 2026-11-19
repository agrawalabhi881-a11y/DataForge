from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DatasetSearchRequest:
    """Payload schema for dataset discovery and ranking requests."""

    query: Optional[str] = None
    domain: Optional[str] = None
    description: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    min_records: Optional[int] = None
    required_features: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    formats: List[str] = field(default_factory=list)
    require_verified_license: bool = False
    max_results_per_source: int = 10

    def validate(self) -> List[str]:
        errors: List[str] = []
        has_search_signal = bool(
            (self.query and self.query.strip())
            or (self.domain and self.domain.strip())
            or (self.description and self.description.strip())
            or self.keywords
        )
        if not has_search_signal:
            errors.append("At least one of query, domain, description, or keywords must be provided.")
        if self.min_records is not None and self.min_records < 0:
            errors.append("min_records must be non-negative.")
        if self.max_results_per_source < 1:
            errors.append("max_results_per_source must be at least 1.")
        return errors

    def to_requirements_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "domain": self.domain,
            "description": self.description,
            "keywords": list(self.keywords),
            "min_records": self.min_records,
            "required_features": list(self.required_features),
            "labels": list(self.labels),
            "formats": list(self.formats),
            "require_verified_license": self.require_verified_license,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatasetSearchRequest":
        raw_formats = data.get("formats")
        if raw_formats is None and data.get("format"):
            raw_formats = [data["format"]]
        return cls(
            query=data.get("query"),
            domain=data.get("domain"),
            description=data.get("description"),
            keywords=list(data.get("keywords") or []),
            min_records=data.get("min_records") if data.get("min_records") is not None else data.get("record_count"),
            required_features=list(data.get("required_features") or data.get("features") or []),
            labels=list(data.get("labels") or []),
            formats=list(raw_formats or []),
            require_verified_license=bool(data.get("require_verified_license", False)),
            max_results_per_source=int(data.get("max_results_per_source", 10)),
        )


@dataclass
class DatasetRecord:
    """Standardized dataset metadata and discovery/registry record."""

    dataset_name: str
    source_id: Optional[str] = None
    dataset_id: Optional[str] = None
    domain: Optional[str] = None
    platform: Optional[str] = None
    source_url: Optional[str] = None
    description: str = ""
    record_count: Optional[int] = None
    features: List[str] = field(default_factory=list)
    format: Optional[str] = None
    formats: List[str] = field(default_factory=list)
    license: Optional[str] = None
    access_status: str = "unknown"
    download_status: str = "pending"
    storage_uri: Optional[str] = None
    checksum: Optional[str] = None
    relevance_score: Optional[float] = None

    def validate(self) -> List[str]:
        errors: List[str] = []
        if not self.dataset_name or not self.dataset_name.strip():
            errors.append("dataset_name must be a non-empty string.")
        if self.record_count is not None and self.record_count < 0:
            errors.append("record_count must be non-negative.")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "dataset_name": self.dataset_name,
            "dataset_id": self.dataset_id,
            "domain": self.domain,
            "platform": self.platform,
            "source_url": self.source_url,
            "description": self.description,
            "record_count": self.record_count,
            "features": list(self.features),
            "format": self.format,
            "formats": list(self.formats),
            "license": self.license,
            "access_status": self.access_status,
            "download_status": self.download_status,
            "storage_uri": self.storage_uri,
            "checksum": self.checksum,
            "relevance_score": self.relevance_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatasetRecord":
        name = data.get("dataset_name") or data.get("name") or data.get("title") or data.get("dataset_id") or ""
        rec_count = data.get("record_count")
        if rec_count is None:
            rec_count = data.get("num_instances")
        return cls(
            dataset_name=str(name),
            source_id=data.get("source_id"),
            dataset_id=data.get("dataset_id") or data.get("dataset_identifier"),
            domain=data.get("domain"),
            platform=data.get("platform"),
            source_url=data.get("source_url") or data.get("url"),
            description=str(data.get("description") or ""),
            record_count=rec_count,
            features=list(data.get("features") or []),
            format=data.get("format"),
            formats=list(data.get("formats") or []),
            license=data.get("license"),
            access_status=str(data.get("access_status") or "unknown"),
            download_status=str(data.get("download_status") or "pending"),
            storage_uri=data.get("storage_uri"),
            checksum=data.get("checksum"),
            relevance_score=data.get("relevance_score"),
        )