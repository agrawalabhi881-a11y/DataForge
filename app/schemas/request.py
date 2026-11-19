from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.core.constants import DOMAINS, FILE_FORMATS, REQUEST_STATUSES

Domain = Literal[*DOMAINS]
OutputFormat = Literal[*FILE_FORMATS]
RequestStatus = Literal[*REQUEST_STATUSES]

MAX_RECORDS = 5_000_000  # request limit, change here if the team agrees on another value
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class RequestCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    project_id: int
    requirements: str = Field(min_length=3, max_length=5000)
    domain: Domain
    record_count: int = Field(gt=0, le=MAX_RECORDS)
    required_features: list[Name] = Field(default_factory=list, max_length=100)
    required_labels: list[Name] = Field(default_factory=list, max_length=50)
    output_format: OutputFormat = "csv"

    @field_validator("required_features", "required_labels")
    @classmethod
    def remove_duplicates(cls, items):
        return list(dict.fromkeys(items))  # keeps the original order


class RequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    requirements: str
    domain: str
    record_count: int
    required_features: list[str]
    required_labels: list[str]
    output_format: str
    strategy: str | None = None
    status: str
    created_at: datetime


class RequestStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    strategy: str | None = None