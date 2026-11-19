from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import ACQUISITION_METHODS, GENERATION_METHODS, JOB_STATUSES
from app.database.base import Base, CreatedAtMixin, check_in


class AcquisitionJob(CreatedAtMixin, Base):
    __tablename__ = "acquisition_jobs"
    __table_args__ = (
        check_in("method", ACQUISITION_METHODS, "ck_acq_method"),
        check_in("status", JOB_STATUSES, "ck_acq_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("data_sources.id", ondelete="CASCADE"), index=True
    )
    request_id: Mapped[int] = mapped_column(
        ForeignKey("dataset_requests.id", ondelete="CASCADE"), index=True
    )
    method: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    download_location: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProcessingJob(CreatedAtMixin, Base):
    __tablename__ = "processing_jobs"
    __table_args__ = (check_in("status", JOB_STATUSES, "ck_proc_status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    stage: Mapped[str | None] = mapped_column(String(50))
    error_details: Mapped[str | None] = mapped_column(Text)
    output_location: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GenerationJob(CreatedAtMixin, Base):
    __tablename__ = "generation_jobs"
    __table_args__ = (
        check_in("method", GENERATION_METHODS, "ck_gen_method"),
        check_in("status", JOB_STATUSES, "ck_gen_status"),
        CheckConstraint("requested_count > 0", name="ck_gen_requested_count"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("dataset_requests.id", ondelete="CASCADE"), index=True
    )
    dataset_id: Mapped[int | None] = mapped_column(
        ForeignKey("datasets.id", ondelete="SET NULL"), index=True
    )
    method: Mapped[str] = mapped_column(String(20))
    requested_count: Mapped[int] = mapped_column(Integer)
    generated_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))