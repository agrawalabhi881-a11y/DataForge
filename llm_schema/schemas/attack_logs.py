from datetime import datetime

from pydantic import Field

from llm_schema.schemas.common import CanonicalRecord


class AttackLogRecord(CanonicalRecord):
    """
    Canonical schema for multi-stage cybersecurity attack logs.
    """

    event_id: str = Field(min_length=1)

    timestamp: datetime | None = None

    source_ip: str | None = None
    destination_ip: str | None = None

    source_port: int | None = Field(default=None, ge=0, le=65535)
    destination_port: int | None = Field(default=None, ge=0, le=65535)

    protocol: str | None = None
    event_type: str | None = None
    attack_stage: str | None = None

    session_id: str | None = None
    campaign_id: str | None = None
    previous_event_id: str | None = None

    label: str | None = None
