from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.dataset import (
    DatasetOut, ExportCreate, ExportOut, LineageOut, QualityReportOut,
)
from app.services import dataset_service

router = APIRouter(prefix="/datasets", tags=["Datasets"])
exports_router = APIRouter(prefix="/exports", tags=["Exports"])


def _get_dataset_or_404(db: Session, user: User, dataset_id: int):
    dataset = dataset_service.get_owned_dataset(
        db, owner_id=user.id, dataset_id=dataset_id
    )
    if dataset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found")
    return dataset


@router.get("", response_model=list[DatasetOut], summary="List my datasets")
def list_datasets(
    project_id: int | None = Query(default=None),
    request_id: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return dataset_service.list_datasets(
        db, owner_id=user.id, project_id=project_id, request_id=request_id,
        limit=limit, offset=offset,
    )


@router.get("/{dataset_id}", response_model=DatasetOut, summary="Get one dataset")
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _get_dataset_or_404(db, user, dataset_id)


@router.get("/{dataset_id}/quality", response_model=QualityReportOut,
            summary="Latest quality report of a dataset")
def get_quality_report(
    dataset_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dataset = _get_dataset_or_404(db, user, dataset_id)
    report = dataset_service.latest_quality_report(db, dataset.id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No quality report yet")
    return report


@router.get("/{dataset_id}/lineage", response_model=list[LineageOut],
            summary="Where the data of this dataset came from")
def get_lineage(
    dataset_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dataset = _get_dataset_or_404(db, user, dataset_id)
    return dataset_service.list_lineage(db, dataset.id)


@router.post("/{dataset_id}/exports", response_model=ExportOut,
             status_code=status.HTTP_201_CREATED,
             summary="Export a validated dataset (mock for now)")
def create_export(
    dataset_id: int,
    body: ExportCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dataset = _get_dataset_or_404(db, user, dataset_id)
    try:
        return dataset_service.create_export(db, dataset, body.file_format)
    except dataset_service.NotExportableError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))


@router.get("/{dataset_id}/exports", response_model=list[ExportOut],
            summary="List exports of a dataset")
def list_exports(
    dataset_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dataset = _get_dataset_or_404(db, user, dataset_id)
    return dataset_service.list_exports(db, dataset.id)


@exports_router.get("/{export_id}", response_model=ExportOut, summary="Get one export")
def get_export(
    export_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    export = dataset_service.get_owned_export(db, owner_id=user.id, export_id=export_id)
    if export is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Export not found")
    return export