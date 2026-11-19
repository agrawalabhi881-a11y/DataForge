from sqlalchemy import Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, CreatedAtMixin


class QualityReport(CreatedAtMixin, Base):
    __tablename__ = "quality_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True
    )
    # Score scale (0-1 or 0-100) must be agreed with Person 5
    completeness_score: Mapped[float | None] = mapped_column(Float)
    validity_score: Mapped[float | None] = mapped_column(Float)
    uniqueness_score: Mapped[float | None] = mapped_column(Float)
    consistency_score: Mapped[float | None] = mapped_column(Float)
    class_distribution: Mapped[dict] = mapped_column(JSONB, default=dict)
    validation_results: Mapped[dict] = mapped_column(JSONB, default=dict)
    warnings: Mapped[list] = mapped_column(JSONB, default=list)
    report_location: Mapped[str | None] = mapped_column(Text)