from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.summary import DashboardStats
from app.services import summary_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats, summary="Counts for my dashboard")
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return summary_service.dashboard_stats(db, user.id)