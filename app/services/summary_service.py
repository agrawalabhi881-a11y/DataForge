from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import REQUEST_STATUSES, SOURCE_TYPES, STRATEGIES
from app.models.dataset import Dataset
from app.models.dataset_request import DatasetRequest
from app.models.export import Export
from app.models.project import Project
from app.services import dataset_service, pipeline_service


def request_summary(db: Session, request: DatasetRequest) -> dict:
    dataset = db.scalar(
        select(Dataset)
        .where(Dataset.request_id == request.id)
        .order_by(Dataset.id.desc())
        .limit(1)
    )
    return {
        "request": request,
        "stages": pipeline_service.list_stages(db, request.id),
        "dataset": dataset,
        "quality_report": (
            dataset_service.latest_quality_report(db, dataset.id) if dataset else None
        ),
        "lineage": dataset_service.list_lineage(db, dataset.id) if dataset else [],
    }


def _fill(keys: tuple, rows) -> dict[str, int]:
    """Every known key appears, even with a count of 0."""
    result = {key: 0 for key in keys}
    for key, count in rows:
        if key is not None:
            result[key] = count
    return result


def dashboard_stats(db: Session, owner_id: int) -> dict:
    project_rows = db.execute(
        select(Project.status, func.count())
        .where(Project.owner_id == owner_id)
        .group_by(Project.status)
    ).all()

    request_base = (
        select(DatasetRequest.status, func.count())
        .join(Project, DatasetRequest.project_id == Project.id)
        .where(Project.owner_id == owner_id)
    )
    request_rows = db.execute(request_base.group_by(DatasetRequest.status)).all()

    strategy_rows = db.execute(
        select(DatasetRequest.strategy, func.count())
        .join(Project, DatasetRequest.project_id == Project.id)
        .where(Project.owner_id == owner_id, DatasetRequest.strategy.is_not(None))
        .group_by(DatasetRequest.strategy)
    ).all()

    dataset_rows = db.execute(
        select(
            Dataset.source_type,
            func.count(),
            func.coalesce(func.sum(Dataset.record_count), 0),
        )
        .join(Project, Dataset.project_id == Project.id)
        .where(Project.owner_id == owner_id)
        .group_by(Dataset.source_type)
    ).all()

    export_count = db.scalar(
        select(func.count())
        .select_from(Export)
        .join(Dataset, Export.dataset_id == Dataset.id)
        .join(Project, Dataset.project_id == Project.id)
        .where(Project.owner_id == owner_id)
    )

    return {
        "projects": _fill(("active", "archived"), project_rows),
        "requests": _fill(REQUEST_STATUSES, request_rows),
        "strategies": _fill(STRATEGIES, strategy_rows),
        "datasets": _fill(SOURCE_TYPES, [(r[0], r[1]) for r in dataset_rows]),
        "total_dataset_records": int(sum(r[2] for r in dataset_rows)),
        "exports": export_count or 0,
    }