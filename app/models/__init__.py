# Import every model here so Alembic can see all tables.
from app.models.user import User
from app.models.project import Project
from app.models.dataset_request import DatasetRequest, DatasetSpecification
from app.models.data_source import DataSource
from app.models.dataset import Dataset
from app.models.job import AcquisitionJob, ProcessingJob, GenerationJob
from app.models.quality_report import QualityReport
from app.models.lineage import DatasetLineage
from app.models.export import Export
from app.models.pipeline_stage import PipelineStage

__all__ = [
    "User", "Project", "DatasetRequest", "DatasetSpecification", "DataSource",
    "Dataset", "AcquisitionJob", "ProcessingJob", "GenerationJob",
    "QualityReport", "DatasetLineage", "Export","PipelineStage",
]