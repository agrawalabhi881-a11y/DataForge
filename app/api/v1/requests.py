from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.schemas.pipeline import StageOut
from app.services import pipeline_service
from app.core.security import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.request import RequestCreate, RequestOut, RequestStatus, RequestStatusOut
from app.services import project_service, request_service
from app.schemas.summary import RequestSummary
from app.services import summary_service

router = APIRouter(prefix="/requests", tags=["Dataset Requests"])


def _get_request_or_404(db: Session, user: User, request_id: int):
    request = request_service.get_owned_request(db, owner_id=user.id, request_id=request_id)
    if request is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    return request


@router.post("", response_model=RequestOut, status_code=status.HTTP_201_CREATED,
             summary="Submit a dataset request")
def create_request(
    body: RequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = project_service.get_owned_project(
        db, owner_id=user.id, project_id=body.project_id
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    if project.status == "archived":
        raise HTTPException(status.HTTP_409_CONFLICT, "Project is archived")
    return request_service.create_request(db, body)


@router.get("", response_model=list[RequestOut], summary="List my dataset requests")
def list_requests(
    project_id: int | None = Query(default=None),
    status_filter: RequestStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return request_service.list_requests(
        db, owner_id=user.id, project_id=project_id, status=status_filter,
        limit=limit, offset=offset,
    )


@router.get("/{request_id}", response_model=RequestOut, summary="Get one dataset request")
def get_request(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _get_request_or_404(db, user, request_id)


@router.get("/{request_id}/status", response_model=RequestStatusOut,
            summary="Get the status of a request")
def get_request_status(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _get_request_or_404(db, user, request_id)


@router.post("/{request_id}/cancel", response_model=RequestOut,
             summary="Cancel a pending or running request")
def cancel_request(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    request = _get_request_or_404(db, user, request_id)
    if request.status not in request_service.CANCELLABLE:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Request is already {request.status}"
        )
    return request_service.cancel_request(db, request)

@router.post("/{request_id}/run", response_model=RequestOut,
             summary="Run the pipeline for a pending request (mock adapters for now)")
def run_request(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    request = _get_request_or_404(db, user, request_id)
    try:
        return pipeline_service.run_pipeline(db, request)
    except pipeline_service.InvalidStateError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))


@router.get("/{request_id}/stages", response_model=list[StageOut],
            summary="Show pipeline progress for a request")
def get_request_stages(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    request = _get_request_or_404(db, user, request_id)
    return pipeline_service.list_stages(db, request.id)

@router.get("/{request_id}/summary", response_model=RequestSummary,
            summary="Everything about a request in one call")
def get_request_summary(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    request = _get_request_or_404(db, user, request_id)
    return summary_service.request_summary(db, request)