from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dataset_request import DatasetRequest
from app.models.project import Project
from app.schemas.request import RequestCreate

CANCELLABLE = ("pending", "processing")


def create_request(db: Session, data: RequestCreate) -> DatasetRequest:
    request = DatasetRequest(
        project_id=data.project_id,
        requirements=data.requirements,
        domain=data.domain,
        record_count=data.record_count,
        required_features=data.required_features,
        required_labels=data.required_labels,
        output_format=data.output_format,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def list_requests(
    db: Session, *, owner_id: int, project_id: int | None, status: str | None,
    limit: int, offset: int,
) -> list[DatasetRequest]:
    # Join with projects so a user only ever sees requests in their own projects
    stmt = (
        select(DatasetRequest)
        .join(Project, DatasetRequest.project_id == Project.id)
        .where(Project.owner_id == owner_id)
    )
    if project_id is not None:
        stmt = stmt.where(DatasetRequest.project_id == project_id)
    if status:
        stmt = stmt.where(DatasetRequest.status == status)
    stmt = stmt.order_by(DatasetRequest.created_at.desc(), DatasetRequest.id.desc())
    return list(db.scalars(stmt.limit(limit).offset(offset)))


def get_owned_request(
    db: Session, *, owner_id: int, request_id: int
) -> DatasetRequest | None:
    return db.scalar(
        select(DatasetRequest)
        .join(Project, DatasetRequest.project_id == Project.id)
        .where(DatasetRequest.id == request_id, Project.owner_id == owner_id)
    )


def cancel_request(db: Session, request: DatasetRequest) -> DatasetRequest:
    request.status = "cancelled"
    db.commit()
    db.refresh(request)
    return request