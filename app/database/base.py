from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """All database models inherit from this class."""
    pass


class CreatedAtMixin:
    """Adds a created_at column that the database fills in automatically."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


def check_in(column: str, values: tuple, name: str) -> CheckConstraint:
    """Database rule: column must be one of the allowed values."""
    options = ", ".join(f"'{v}'" for v in values)
    return CheckConstraint(f"{column} IN ({options})", name=name)