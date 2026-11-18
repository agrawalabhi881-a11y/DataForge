from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class DatasetDomain(StrEnum):
    PHISHING_URLS = "phishing_urls"
    ATTACK_LOGS = "attack_logs"
    VULNERABLE_CODE = "vulnerable_code"
    USER_BEHAVIOR = "user_behavior"


class SourceType(StrEnum):
    REAL = "real"
    SYNTHETIC = "synthetic"
    UNKNOWN = "unknown"


class CanonicalRecord(BaseModel):
    """
    Shared base model for all DataForge canonical records.

    Extra fields are allowed so that source-specific information
    is not silently discarded during schema validation.
    """

    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    source_type: SourceType = SourceType.UNKNOWN
    source_id: str | None = None
