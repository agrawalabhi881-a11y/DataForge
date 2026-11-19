from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import FILE_FORMATS, JOB_STATUSES
from app.database.base import Base, CreatedAtMixin, check_in


class Export(CreatedAtMixin, Base):
    __tablename__ = "exports"
    __table_args__ = (
        check_in("file_format", FILE_FORMATS, "ck_exports_file_format"),
        check_in("status", JOB_STATUSES, "ck_exports_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True
    )
    file_format: Mapped[str] = mapped_column(String(10))
    export_location: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))