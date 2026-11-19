from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import (
    DOMAINS, FILE_FORMATS, REQUEST_STATUSES, STRATEGIES, VALIDATION_STATUSES,
)
from app.database.base import Base, CreatedAtMixin, check_in


class DatasetRequest(CreatedAtMixin, Base):
    __tablename__ = "dataset_requests"
    __table_args__ = (
        check_in("domain", DOMAINS, "ck_requests_domain"),
        check_in("output_format", FILE_FORMATS, "ck_requests_output_format"),
        check_in("strategy", STRATEGIES, "ck_requests_strategy"),
        check_in("status", REQUEST_STATUSES, "ck_requests_status"),
        CheckConstraint("record_count > 0", name="ck_requests_record_count"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    requirements: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String(30))
    record_count: Mapped[int] = mapped_column(Integer)
    required_features: Mapped[list] = mapped_column(JSONB, default=list)
    required_labels: Mapped[list] = mapped_column(JSONB, default=list)
    output_format: Mapped[str] = mapped_column(String(10), default="csv")
    # Filled in later by the adaptive strategy engine (NULL until decided)
    strategy: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending"
    )


class DatasetSpecification(CreatedAtMixin, Base):
    __tablename__ = "dataset_specifications"
    __table_args__ = (
        check_in("domain", DOMAINS, "ck_specs_domain"),
        check_in("validation_status", VALIDATION_STATUSES, "ck_specs_validation_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("dataset_requests.id", ondelete="CASCADE"), index=True
    )
    domain: Mapped[str] = mapped_column(String(30))
    dataset_type: Mapped[str] = mapped_column(String(60))
    feature_definitions: Mapped[list] = mapped_column(JSONB, default=list)
    label_definitions: Mapped[list] = mapped_column(JSONB, default=list)
    class_distribution: Mapped[dict] = mapped_column(JSONB, default=dict)
    schema_version: Mapped[str] = mapped_column(String(10), default="1.0")
    validation_status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending"
    )