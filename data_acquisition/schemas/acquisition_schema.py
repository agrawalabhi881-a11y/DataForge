from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AcquisitionRequest:
    """Payload schema for triggering dataset download and raw storage ingestion."""

    dataset_id: str
    download_url: Optional[str] = None
    connector_name: Optional[str] = None
    domain: Optional[str] = None
    filename: Optional[str] = None
    expected_sha256: Optional[str] = None
    extract_archives: bool = False
    overwrite: bool = False

    def validate(self) -> List[str]:
        errors: List[str] = []
        if not self.dataset_id or not self.dataset_id.strip():
            errors.append("dataset_id must be a non-empty string.")
        if self.expected_sha256:
            cleaned = self.expected_sha256.strip()
            if len(cleaned) != 64 or any(c not in "0123456789abcdefABCDEF" for c in cleaned):
                errors.append("expected_sha256 must be a 64-character hex string.")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "download_url": self.download_url,
            "connector_name": self.connector_name,
            "domain": self.domain,
            "filename": self.filename,
            "expected_sha256": self.expected_sha256,
            "extract_archives": self.extract_archives,
            "overwrite": self.overwrite,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AcquisitionRequest":
        return cls(
            dataset_id=str(data.get("dataset_id") or data.get("source_id") or ""),
            download_url=data.get("download_url") or data.get("source_url"),
            connector_name=data.get("connector_name"),
            domain=data.get("domain"),
            filename=data.get("filename"),
            expected_sha256=data.get("expected_sha256"),
            extract_archives=bool(data.get("extract_archives", False)),
            overwrite=bool(data.get("overwrite", False)),
        )


@dataclass
class AcquisitionJobStatus:
    """Standardized status payload returned by acquisition and download jobs."""

    job_id: str
    source_id: str
    status: str = "pending"
    storage_uri: Optional[str] = None
    checksum: Optional[str] = None
    file_size_bytes: Optional[int] = None
    attempts: int = 0
    error: Optional[str] = None

    VALID_STATUSES = {"pending", "downloading", "retrying", "completed", "failed"}

    def validate(self) -> List[str]:
        errors: List[str] = []
        if not self.job_id:
            errors.append("job_id is required.")
        if not self.source_id:
            errors.append("source_id is required.")
        if self.status not in self.VALID_STATUSES:
            errors.append(f"Invalid status '{self.status}'. Expected one of {sorted(self.VALID_STATUSES)}.")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "source_id": self.source_id,
            "status": self.status,
            "storage_uri": self.storage_uri,
            "checksum": self.checksum,
            "file_size_bytes": self.file_size_bytes,
            "attempts": self.attempts,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AcquisitionJobStatus":
        return cls(
            job_id=str(data.get("job_id") or ""),
            source_id=str(data.get("source_id") or ""),
            status=str(data.get("status") or "pending"),
            storage_uri=data.get("storage_uri"),
            checksum=data.get("checksum"),
            file_size_bytes=data.get("file_size_bytes"),
            attempts=int(data.get("attempts") or 0),
            error=data.get("error"),
        )


@dataclass
class ProvenanceRecord:
    """Provenance and integrity record for an acquired raw dataset."""

    source_id: str
    source_url: Optional[str] = None
    platform: Optional[str] = None
    domain: Optional[str] = None
    storage_uri: Optional[str] = None
    sha256: Optional[str] = None
    license: Optional[str] = None
    acquired_at: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "source_id": self.source_id,
            "source_url": self.source_url,
            "platform": self.platform,
            "domain": self.domain,
            "storage_uri": self.storage_uri,
            "sha256": self.sha256,
            "license": self.license,
            "acquired_at": self.acquired_at,
        }
        if self.extra:
            payload["extra"] = dict(self.extra)
        return payload

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProvenanceRecord":
        return cls(
            source_id=str(data.get("source_id") or ""),
            source_url=data.get("source_url"),
            platform=data.get("platform"),
            domain=data.get("domain"),
            storage_uri=data.get("storage_uri"),
            sha256=data.get("sha256") or data.get("checksum"),
            license=data.get("license"),
            acquired_at=data.get("acquired_at"),
            extra=dict(data.get("extra") or {}),
        )