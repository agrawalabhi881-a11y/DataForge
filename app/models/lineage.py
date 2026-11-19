from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import GENERATION_METHODS
from app.database.base import Base, CreatedAtMixin, check_in


class DatasetLineage(CreatedAtMixin, Base):
    """Tells us where each record (or partition) of a dataset came from."""
    __tablename__ = "dataset_lineage"
    __table_args__ = (
        check_in("source_type", ("real", "synthetic"), "ck_lineage_source_type"),
        check_in("generation_method", GENERATION_METHODS, "ck_lineage_generation_method"),
        # Real records have a source and no generation method.
        # Synthetic records have a generation method and no source.
        CheckConstraint(
            "(source_type = 'real' AND generation_method IS NULL) OR "
            "(source_type = 'synthetic' AND original_source_id IS NULL "
            "AND generation_method IS NOT NULL)",
            name="ck_lineage_provenance",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True
    )
    record_ref: Mapped[str | None] = mapped_column(String(100))  # record id or partition name
    source_type: Mapped[str] = mapped_column(String(20))
    original_source_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"), index=True
    )
    generation_method: Mapped[str | None] = mapped_column(String(20))
    transformation_history: Mapped[list] = mapped_column(JSONB, default=list)