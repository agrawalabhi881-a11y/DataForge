from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.core.constants import FILE_FORMATS

ExportFormat = Literal[*FILE_FORMATS]


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_code: str | None = None
    project_id: int
    request_id: int | None = None
    name: str
    domain: str
    dataset_type: str
    record_count: int
    features: list
    storage_uri: str | None = None
    file_format: str
    stage: str
    source_type: str
    quality_status: str
    schema_version: str
    created_at: datetime


class QualityReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    completeness_score: float | None = None
    validity_score: float | None = None
    uniqueness_score: float | None = None
    consistency_score: float | None = None
    class_distribution: dict
    validation_results: dict
    warnings: list
    report_location: str | None = None
    created_at: datetime


class LineageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    record_ref: str | None = None
    source_type: str
    original_source_id: int | None = None
    generation_method: str | None = None
    transformation_history: list
    created_at: datetime


class ExportCreate(BaseModel):
    file_format: ExportFormat


class ExportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    file_format: str
    export_location: str | None = None
    status: str
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None