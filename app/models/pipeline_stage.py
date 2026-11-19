from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import JOB_STATUSES
from app.database.base import Base, CreatedAtMixin, check_in


class PipelineStage(CreatedAtMixin, Base):
    """One row per stage of a pipeline run, so the user can see progress."""
    __tablename__ = "pipeline_stages"
    __table_args__ = (check_in("status", JOB_STATUSES, "ck_stages_status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("dataset_requests.id", ondelete="CASCADE"), index=True
    )
    stage: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="running")
    message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))