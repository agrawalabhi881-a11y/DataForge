from datetime import datetime

from pydantic import Field

from llm_schema.schemas.common import CanonicalRecord


class UserBehaviorRecord(CanonicalRecord):
    """
    Canonical schema for user behavior and anomaly sequences.
    """

    event_id: str = Field(min_length=1)

    user_id: str | None = None
    timestamp: datetime | None = None
    session_id: str | None = None

    activity_type: str | None = None
    device: str | None = None
    resource: str | None = None

    duration: float | None = Field(default=None, ge=0)
    anomaly_score: float | None = Field(default=None, ge=0, le=1)

    label: str | None = None
