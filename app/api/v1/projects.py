from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectOut, ProjectStatus, ProjectUpdate
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["Projects"])


def _get_project_or_404(db: Session, user: User, project_id: int):
    project = project_service.get_owned_project(
        db, owner_id=user.id, project_id=project_id
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED,
             summary="Create a project")
def create_project(
    body: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return project_service.create_project(
        db, owner_id=user.id, name=body.name, description=body.description
    )


@router.get("", response_model=list[ProjectOut], summary="List my projects")
def list_projects(
    status_filter: ProjectStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return project_service.list_projects(
        db, owner_id=user.id, status=status_filter, limit=limit, offset=offset
    )


@router.get("/{project_id}", response_model=ProjectOut, summary="Get one project")
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _get_project_or_404(db, user, project_id)


@router.patch("/{project_id}", response_model=ProjectOut,
              summary="Rename, edit or archive a project")
def update_project(
    project_id: int,
    body: ProjectUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _get_project_or_404(db, user, project_id)
    changes = body.model_dump(exclude_unset=True)
    return project_service.update_project(db, project, changes)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a project and everything inside it")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _get_project_or_404(db, user, project_id)
    project_service.delete_project(db, project)