"""Fake versions of Person 3-6's work. Replace these functions with real calls later."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.data_source import DataSource
from app.models.dataset_request import DatasetRequest
from app.schemas.strategy import RealDataAssessment


def discover_sources(db: Session, domain: str) -> list[DataSource]:
    """Mock for Person 3/4: returns one verified source per domain."""
    identifier = f"mock-{domain}"
    source = db.scalar(
        select(DataSource).where(
            DataSource.platform == "mock", DataSource.dataset_identifier == identifier
        )
    )
    if source is None:
        source = DataSource(
            name=f"Mock {domain} source",
            platform="mock",
            source_url=f"mock://{domain}",
            dataset_identifier=identifier,
            domain=domain,
            license_info="Mock open license",
            license_status="verified_open",
        )
        db.add(source)
        db.commit()
        db.refresh(source)
    return [source]


def assess_real_data(request: DatasetRequest) -> RealDataAssessment:
    """Mock for Person 5: pretends 60% of the records exist, one feature is
    missing and the first label dominates. Scores are 0 to 1."""
    available = int(request.record_count * 0.6)
    features = list(request.required_features)
    if len(features) > 1:
        features = features[:-1]

    labels = list(request.required_labels)
    counts: dict[str, int] = {}
    if len(labels) == 1:
        counts[labels[0]] = available
    elif labels:
        first = int(available * 0.7)
        rest = (available - first) // (len(labels) - 1)
        counts[labels[0]] = first
        for label in labels[1:]:
            counts[label] = rest

    return RealDataAssessment(
        available_record_count=available,
        available_features=features,
        label_counts=counts,
        completeness=0.9, validity=0.9, consistency=0.9, relevance=0.9,
    )