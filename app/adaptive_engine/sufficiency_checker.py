"""Small, separate checks. Each one answers a single question about the real data."""
import math

from app.adaptive_engine.decision_config import DecisionConfig
from app.schemas.strategy import RealDataAssessment, SourceEligibility


def _key(name: str) -> str:
    return name.strip().lower()


def _unique(names: list[str]) -> list[str]:
    seen, result = set(), []
    for name in names:
        if _key(name) not in seen:
            seen.add(_key(name))
            result.append(name.strip())
    return result


def split_sources(sources: list[SourceEligibility], config: DecisionConfig):
    """Returns (ids of eligible sources, a problem message for each ineligible one)."""
    eligible, problems = [], []
    for source in sources:
        if not source.acquired:
            problems.append(f"Source {source.source_id} was not acquired")
        elif not source.access_ok:
            problems.append(f"Source {source.source_id} has access conditions we cannot meet")
        elif source.license_status not in config.allowed_license_statuses:
            problems.append(
                f"Source {source.source_id} license is '{source.license_status}', "
                f"not one of {list(config.allowed_license_statuses)}"
            )
        else:
            eligible.append(source.source_id)
    return eligible, problems


def feature_gap(required: list[str], available: list[str]):
    required = _unique(required)
    have = {_key(name) for name in available}
    missing = [name for name in required if _key(name) not in have]
    coverage = 1.0 if not required else (len(required) - len(missing)) / len(required)
    return coverage, missing


def label_gap(required: list[str], label_counts: dict[str, int]):
    required = _unique(required)
    counts: dict[str, int] = {}
    for label, count in label_counts.items():
        counts[_key(label)] = counts.get(_key(label), 0) + count
    missing = [label for label in required if counts.get(_key(label), 0) == 0]
    coverage = 1.0 if not required else (len(required) - len(missing)) / len(required)
    return coverage, missing, counts


def per_class_minimum(target: int, label_count: int, config: DecisionConfig) -> int:
    if label_count < 2:  # one label alone has no balance to check
        return 0
    share = min(config.min_class_share, 1 / label_count)
    return math.ceil(target * share)


def class_shortfalls(required_labels, counts, target, config) -> dict[str, int]:
    required = _unique(required_labels)
    minimum = per_class_minimum(target, len(required), config)
    shortfalls = {}
    for label in required:
        missing = minimum - counts.get(_key(label), 0)
        if missing > 0:
            shortfalls[label] = missing
    return shortfalls


def records_are_short(target: int, available: int, config: DecisionConfig) -> bool:
    return available < math.ceil(target * config.min_record_ratio)


def quality_scores(assessment: RealDataAssessment) -> dict[str, float]:
    return {
        "completeness": assessment.completeness,
        "validity": assessment.validity,
        "consistency": assessment.consistency,
    }


def dimensions_below(assessment: RealDataAssessment, limit: float) -> list[str]:
    return [name for name, score in quality_scores(assessment).items() if score < limit]