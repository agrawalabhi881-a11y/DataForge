from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.export import Export
from app.models.lineage import DatasetLineage
from app.models.project import Project
from app.models.quality_report import QualityReport


def list_datasets(
    db: Session, *, owner_id: int, project_id: int | None, request_id: int | None,
    limit: int, offset: int,
) -> list[Dataset]:
    stmt = (
        select(Dataset)
        .join(Project, Dataset.project_id == Project.id)
        .where(Project.owner_id == owner_id)
    )
    if project_id is not None:
        stmt = stmt.where(Dataset.project_id == project_id)
    if request_id is not None:
        stmt = stmt.where(Dataset.request_id == request_id)
    stmt = stmt.order_by(Dataset.created_at.desc(), Dataset.id.desc())
    return list(db.scalars(stmt.limit(limit).offset(offset)))


def get_owned_dataset(db: Session, *, owner_id: int, dataset_id: int) -> Dataset | None:
    return db.scalar(
        select(Dataset)
        .join(Project, Dataset.project_id == Project.id)
        .where(Dataset.id == dataset_id, Project.owner_id == owner_id)
    )


def latest_quality_report(db: Session, dataset_id: int) -> QualityReport | None:
    return db.scalar(
        select(QualityReport)
        .where(QualityReport.dataset_id == dataset_id)
        .order_by(QualityReport.created_at.desc(), QualityReport.id.desc())
        .limit(1)
    )


def list_lineage(db: Session, dataset_id: int) -> list[DatasetLineage]:
    return list(
        db.scalars(
            select(DatasetLineage)
            .where(DatasetLineage.dataset_id == dataset_id)
            .order_by(DatasetLineage.id)
        )
    )


class NotExportableError(Exception):
    """The dataset has not passed quality validation."""


def create_export(db: Session, dataset: Dataset, file_format: str) -> Export:
    if dataset.quality_status != "validated":
        raise NotExportableError(
            f"Dataset is '{dataset.quality_status}', only validated datasets can be exported"
        )
    # Mock export: a real worker will write the file and fill in the real location.
    export = Export(
        dataset_id=dataset.id,
        file_format=file_format,
        export_location=f"mock://exports/{dataset.dataset_code}.{file_format}",
        status="completed",
        completed_at=datetime.now(timezone.utc),
    )
    db.add(export)
    db.commit()
    db.refresh(export)
    return export


def list_exports(db: Session, dataset_id: int) -> list[Export]:
    return list(
        db.scalars(
            select(Export)
            .where(Export.dataset_id == dataset_id)
            .order_by(Export.created_at.desc(), Export.id.desc())
        )
    )


def get_owned_export(db: Session, *, owner_id: int, export_id: int) -> Export | None:
    return db.scalar(
        select(Export)
        .join(Dataset, Export.dataset_id == Dataset.id)
        .join(Project, Dataset.project_id == Project.id)
        .where(Export.id == export_id, Project.owner_id == owner_id)
    )