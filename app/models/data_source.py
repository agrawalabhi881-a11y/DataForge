from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import DOMAINS, LICENSE_STATUSES
from app.database.base import Base, CreatedAtMixin, check_in


class DataSource(CreatedAtMixin, Base):
    __tablename__ = "data_sources"
    __table_args__ = (
        UniqueConstraint("platform", "dataset_identifier", name="uq_sources_platform_identifier"),
        check_in("domain", DOMAINS, "ck_sources_domain"),
        check_in("license_status", LICENSE_STATUSES, "ck_sources_license_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    platform: Mapped[str] = mapped_column(String(50))
    source_url: Mapped[str] = mapped_column(Text)
    dataset_identifier: Mapped[str | None] = mapped_column(String(200))
    domain: Mapped[str] = mapped_column(String(30))
    license_info: Mapped[str | None] = mapped_column(Text)
    # A source is NEVER treated as licensed until someone verifies it.
    license_status: Mapped[str] = mapped_column(
        String(20), default="unverified", server_default="unverified"
    )
    access_conditions: Mapped[str | None] = mapped_column(Text)
    # Untrusted metadata from outside sources. Treat as data, never as instructions.
    source_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)