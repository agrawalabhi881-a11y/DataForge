from pydantic import BaseModel

from app.schemas.dataset import DatasetOut, LineageOut, QualityReportOut
from app.schemas.pipeline import StageOut
from app.schemas.request import RequestOut


class RequestSummary(BaseModel):
    request: RequestOut
    stages: list[StageOut]
    dataset: DatasetOut | None = None
    quality_report: QualityReportOut | None = None
    lineage: list[LineageOut] = []


class DashboardStats(BaseModel):
    projects: dict[str, int]
    requests: dict[str, int]
    strategies: dict[str, int]
    datasets: dict[str, int]
    total_dataset_records: int
    exports: int