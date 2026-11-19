from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters import mock_adapters
from app.adaptive_engine.strategy_selector import select_strategy
from app.models.dataset import Dataset
from app.models.dataset_request import DatasetRequest
from app.models.job import AcquisitionJob, GenerationJob
from app.models.lineage import DatasetLineage
from app.models.pipeline_stage import PipelineStage
from app.models.quality_report import QualityReport
from app.schemas.strategy import Requirements, SourceEligibility


class InvalidStateError(Exception):
    """The request is not in a state that allows this action."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


@contextmanager
def tracked_stage(db: Session, request_id: int, name: str):
    """Records the stage as running, then completed or failed."""
    row = PipelineStage(
        request_id=request_id, stage=name, status="running", started_at=_now()
    )
    db.add(row)
    db.commit()
    stage_id = row.id
    try:
        yield row
    except Exception as exc:
        db.rollback()
        failed = db.get(PipelineStage, stage_id)
        failed.status = "failed"
        failed.message = str(exc)[:500]
        failed.completed_at = _now()
        db.commit()
        raise
    else:
        row.status = "completed"
        row.completed_at = _now()
        db.commit()


def list_stages(db: Session, request_id: int) -> list[PipelineStage]:
    return list(
        db.scalars(
            select(PipelineStage)
            .where(PipelineStage.request_id == request_id)
            .order_by(PipelineStage.id)
        )
    )


def run_pipeline(db: Session, request: DatasetRequest) -> DatasetRequest:
    if request.status != "pending":
        raise InvalidStateError(f"Only a pending request can run (this one is {request.status})")

    request_id = request.id
    request.status = "processing"
    db.commit()

    try:
        _execute(db, request)
        request.status = "completed"
        db.commit()
    except Exception:
        db.rollback()
        request = db.get(DatasetRequest, request_id)
        request.status = "failed"
        db.commit()
    db.refresh(request)
    return request


def _execute(db: Session, request: DatasetRequest) -> None:
    # 1. Sources
    with tracked_stage(db, request.id, "source_discovery") as stage:
        sources = mock_adapters.discover_sources(db, request.domain)
        stage.message = f"{len(sources)} source(s) found"

    # 2. Real-data assessment + strategy decision
    with tracked_stage(db, request.id, "strategy_selection") as stage:
        assessment = mock_adapters.assess_real_data(request)
        eligibility = [
            SourceEligibility(
                source_id=s.id, license_status=s.license_status,
                access_ok=True, acquired=True,
            )
            for s in sources
        ]
        decision = select_strategy(
            Requirements(
                domain=request.domain,
                record_count=request.record_count,
                required_features=request.required_features,
                required_labels=request.required_labels,
            ),
            assessment,
            eligibility,
        )
        request.strategy = decision.strategy
        stage.message = f"{decision.strategy}: " + "; ".join(decision.reasons)[:400]

    plan = decision.generation_plan
    uses_real = decision.strategy != "synthetic_only"
    generate_count = plan.records_to_generate if plan else 0
    job = None

    # 3. Acquisition (real data only)
    if uses_real:
        with tracked_stage(db, request.id, "acquisition") as stage:
            for source in sources:
                db.add(AcquisitionJob(
                    source_id=source.id, request_id=request.id,
                    method="direct_download", status="completed",
                    download_location=f"mock://downloads/{source.id}",
                    completed_at=_now(),
                ))
            stage.message = "Mock download finished"

    # 4. Generation (synthetic data)
    if generate_count > 0:
        with tracked_stage(db, request.id, "generation") as stage:
            job = GenerationJob(
                request_id=request.id, method="rule_based",
                requested_count=generate_count, generated_count=generate_count,
                status="completed", config=plan.model_dump(), completed_at=_now(),
            )
            db.add(job)
            stage.message = f"Mock generated {generate_count} records"

    # 5. Dataset, lineage, quality report
    with tracked_stage(db, request.id, "dataset_build") as stage:
        source_type = {
            "real_only": "real",
            "synthetic_only": "synthetic",
            "real_plus_synthetic": "mixed",
        }[decision.strategy]

        dataset = Dataset(
            project_id=request.project_id,
            request_id=request.id,
            name=f"Dataset for request {request.id}",
            domain=request.domain,
            dataset_type=f"{request.domain}_dataset",
            record_count=request.record_count,
            features=request.required_features,
            storage_uri=f"mock://datasets/request_{request.id}",
            file_format=request.output_format,
            stage="final",
            source_type=source_type,
            quality_status="validated",
        )
        db.add(dataset)
        db.flush()
        dataset.dataset_code = f"DF_{dataset.id:06d}"
        if job is not None:
            job.dataset_id = dataset.id

        if uses_real:
            db.add(DatasetLineage(
                dataset_id=dataset.id, record_ref="real_partition",
                source_type="real", original_source_id=sources[0].id,
                transformation_history=["mock_download", "mock_cleaning"],
            ))
        if generate_count > 0 or not uses_real:
            db.add(DatasetLineage(
                dataset_id=dataset.id, record_ref="synthetic_partition",
                source_type="synthetic", generation_method="rule_based",
                transformation_history=["mock_generation"],
            ))

        db.add(QualityReport(
            dataset_id=dataset.id,
            completeness_score=assessment.completeness,
            validity_score=assessment.validity,
            uniqueness_score=1.0,
            consistency_score=assessment.consistency,
            class_distribution=assessment.label_counts,
            validation_results={"mock": True},
            warnings=decision.warnings,
        ))
        stage.message = f"Created {dataset.dataset_code} ({source_type})"