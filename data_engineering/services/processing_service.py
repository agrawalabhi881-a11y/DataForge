"""DataForge - Data Engineering: configurable, non-destructive pipeline orchestration."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

import pandas as pd


@dataclass(frozen=True)
class ProcessingStep:
    name: str
    operation: Callable[..., Any]
    parameters: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingResult:
    dataframe: pd.DataFrame
    steps: list[dict[str, Any]]
    warnings: list[str]
    metadata: dict[str, Any]


def _extract_frame(value: Any) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value
    frame = getattr(value, "dataframe", None)
    if isinstance(frame, pd.DataFrame):
        return frame
    raise TypeError("Processing step must return a DataFrame or an object with a DataFrame 'dataframe' attribute.")


def process_dataset(
    dataframe: pd.DataFrame,
    steps: Sequence[ProcessingStep] = (),
    *,
    dataset_id: str | None = None,
    domain: str | None = None,
) -> ProcessingResult:
    """Run explicit processing steps on copies; retain source data and audit metadata.

    The caller selects and configures domain/cleaning/schema functions. This
    service does not infer mappings, change source labels, or drop invalid rows.
    """
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a pandas DataFrame")
    if not dataframe.columns.is_unique:
        raise ValueError("Column names must be unique")
    if not isinstance(steps, (list, tuple)):
        raise TypeError("steps must be a list or tuple of ProcessingStep")
    current = dataframe.copy(deep=True)
    audit: list[dict[str, Any]] = []
    warnings: list[str] = []
    for position, step in enumerate(steps, start=1):
        if not isinstance(step, ProcessingStep):
            raise TypeError(f"Step {position} must be a ProcessingStep")
        if not step.name.strip() or not callable(step.operation):
            raise ValueError(f"Step {position} requires a name and callable")
        before = len(current)
        try:
            output = step.operation(current.copy(deep=True), **dict(step.parameters))
            next_frame = _extract_frame(output)
        except Exception as exc:
            raise RuntimeError(f"Processing step {position} ({step.name}) failed") from exc
        current = next_frame.copy(deep=True)
        record = {"step": position, "name": step.name, "rows_before": before,
                  "rows_after": len(current)}
        transformations = getattr(output, "transformations", None)
        if transformations is not None:
            record["transformations"] = transformations
        audit.append(record)
        step_warnings = getattr(output, "warnings", None)
        if step_warnings:
            warnings.extend(str(item) for item in step_warnings)
    return ProcessingResult(
        dataframe=current, steps=audit, warnings=warnings,
        metadata={"dataset_id": dataset_id, "domain": domain,
                  "rows_input": len(dataframe), "rows_output": len(current),
                  "steps_executed": len(audit)},
    )
