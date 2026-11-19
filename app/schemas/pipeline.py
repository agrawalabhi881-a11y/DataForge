from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stage: str
    status: str
    message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None