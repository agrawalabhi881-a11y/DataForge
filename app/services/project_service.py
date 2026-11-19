from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project


def create_project(
    db: Session, *, owner_id: int, name: str, description: str | None
) -> Project:
    project = Project(owner_id=owner_id, name=name, description=description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def list_projects(
    db: Session, *, owner_id: int, status: str | None, limit: int, offset: int
) -> list[Project]:
    stmt = select(Project).where(Project.owner_id == owner_id)
    if status:
        stmt = stmt.where(Project.status == status)
    stmt = stmt.order_by(Project.created_at.desc(), Project.id.desc())
    return list(db.scalars(stmt.limit(limit).offset(offset)))


def get_owned_project(db: Session, *, owner_id: int, project_id: int) -> Project | None:
    """Returns the project only if it belongs to this user."""
    return db.scalar(
        select(Project).where(Project.id == project_id, Project.owner_id == owner_id)
    )


def update_project(db: Session, project: Project, changes: dict) -> Project:
    for field, value in changes.items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project) -> None:
    db.delete(project)
    db.commit()