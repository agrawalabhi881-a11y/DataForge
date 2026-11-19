from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import (
    DATASET_STAGES, DOMAINS, FILE_FORMATS, QUALITY_STATUSES, SOURCE_TYPES,
)
from app.database.base import Base, CreatedAtMixin, check_in


class Dataset(CreatedAtMixin, Base):
    __tablename__ = "datasets"
    __table_args__ = (
        check_in("domain", DOMAINS, "ck_datasets_domain"),
        check_in("file_format", FILE_FORMATS, "ck_datasets_file_format"),
        check_in("stage", DATASET_STAGES, "ck_datasets_stage"),
        check_in("source_type", SOURCE_TYPES, "ck_datasets_source_type"),
        check_in("quality_status", QUALITY_STATUSES, "ck_datasets_quality_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_code: Mapped[str | None] = mapped_column(String(20), unique=True)  # e.g. DF_000001
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    request_id: Mapped[int | None] = mapped_column(
        ForeignKey("dataset_requests.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    domain: Mapped[str] = mapped_column(String(30))
    dataset_type: Mapped[str] = mapped_column(String(60))
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    features: Mapped[list] = mapped_column(JSONB, default=list)
    storage_uri: Mapped[str | None] = mapped_column(Text)
    file_format: Mapped[str] = mapped_column(String(10), default="parquet")
    stage: Mapped[str] = mapped_column(String(20), default="raw")  # raw/processed/synthetic/final
    source_type: Mapped[str] = mapped_column(String(20))  # real / synthetic / mixed
    quality_status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending"
    )
    schema_version: Mapped[str] = mapped_column(String(10), default="1.0")