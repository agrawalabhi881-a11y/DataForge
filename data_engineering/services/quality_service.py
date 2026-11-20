"""DataForge - Data Engineering: structured quality report service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

import pandas as pd


@dataclass
class QualityServiceResult:
    report: dict[str, Any]
    dataset_id: str | None
    domain: str | None


def assess_dataset_quality(
    dataframe: pd.DataFrame,
    *,
    dataset_id: str | None = None,
    domain: str | None = None,
    required_columns: list[str] | None = None,
    required_features: list[str] | None = None,
    report_generator: Callable[..., dict[str, Any]] | None = None,
    report_options: Mapping[str, Any] | None = None,
) -> QualityServiceResult:
    """Delegate to the installed quality engine without modifying input data.

    report_generator can be injected for compatibility/testing. By default,
    the project's quality_report.generate_quality_report is imported lazily.
    """
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a pandas DataFrame")
    if report_generator is None:
        from data_engineering.quality.quality_report import generate_quality_report
        report_generator = generate_quality_report
    if not callable(report_generator):
        raise TypeError("report_generator must be callable")
    options = dict(report_options or {})
    reserved = {"dataset_id", "domain", "required_columns", "required_features"}
    overlap = reserved.intersection(options)
    if overlap:
        raise ValueError(f"Reserved report_options keys: {sorted(overlap)}")
    report = report_generator(
        dataframe.copy(deep=True),
        dataset_id=dataset_id,
        domain=domain,
        required_columns=required_columns or [],
        required_features=required_features or [],
        **options,
    )
    if not isinstance(report, dict):
        raise TypeError("Quality report generator must return a dictionary")
    return QualityServiceResult(report=report, dataset_id=dataset_id, domain=domain)
