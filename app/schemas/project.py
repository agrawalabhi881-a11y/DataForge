from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ProjectStatus = Literal["active", "archived"]


class ProjectCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)


class ProjectUpdate(BaseModel):
    """All fields are optional. Only the fields you send are changed."""
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    status: ProjectStatus | None = None

    @field_validator("name", "status")
    @classmethod
    def not_null(cls, value):
        # These columns can't be NULL, so reject an explicit null.
        if value is None:
            raise ValueError("This field cannot be null")
        return value


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    status: str
    owner_id: int
    created_at: datetime