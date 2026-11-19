from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import get_db

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    dependencies: dict[str, str]
    time: str


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    database = "down"
    try:
        db.execute(text("SELECT 1"))
        database = "up"
    except Exception as err:
        print("Health check: database error:", err)

    body = HealthResponse(
        status="ok" if database == "up" else "degraded",
        service="dataforge-backend",
        dependencies={"database": database},
        time=datetime.now(timezone.utc).isoformat(),
    )
    code = 200 if database == "up" else 503
    return JSONResponse(status_code=code, content=body.model_dump())