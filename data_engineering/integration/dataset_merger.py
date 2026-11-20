"""DataForge - Data Engineering: non-destructive real/synthetic dataset integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import pandas as pd

from .provenance_manager import validate_provenance
from .record_id_generator import assign_record_ids


@dataclass
class DatasetMergeResult:
    dataframe: pd.DataFrame
    statistics: dict[str, Any]
    transformations: list[dict[str, Any]]
    warnings: list[str]


def merge_datasets(
    real_dataframe: pd.DataFrame | None = None,
    synthetic_dataframe: pd.DataFrame | None = None,
    *,
    id_column: str = 'record_id',
    required_columns: list[str] | None = None,
    deduplicate_on: list[str] | None = None,
    generate_missing_ids: bool = True,
) -> DatasetMergeResult:
    """Combine compatible records, requiring explicit valid provenance for every input.

    The function never silently drops duplicates, changes labels, or infers origins.
    It raises on ID collisions and duplicate keys; deduplicate_on is an audit check.
    """
    inputs = [('real', real_dataframe), ('synthetic', synthetic_dataframe)]
    active = [(kind, frame) for kind, frame in inputs if frame is not None]
    if not active:
        raise ValueError('Provide at least one dataset')
    for kind, frame in active:
        if not isinstance(frame, pd.DataFrame):
            raise TypeError(f'{kind} dataset must be a pandas DataFrame')
        if not frame.columns.is_unique:
            raise ValueError(f'{kind} dataset has duplicate column names')
        audit = validate_provenance(frame)
        if not audit['valid']:
            raise ValueError(f'{kind} provenance invalid: {audit["errors"][:5]}')
        if not frame['source_type'].eq(kind).all():
            raise ValueError(f'{kind} input contains incorrect source_type values')
    if not isinstance(id_column, str) or not id_column:
        raise ValueError('id_column must be a nonempty string')
    for name, cols in [('required_columns', required_columns), ('deduplicate_on', deduplicate_on)]:
        if cols is not None and (not isinstance(cols, list) or not all(isinstance(c, str) and c for c in cols)):
            raise TypeError(f'{name} must be a list of nonempty column names')
    all_columns = list(dict.fromkeys(c for _, frame in active for c in frame.columns))
    required = required_columns or []
    absent = [c for c in required if c not in all_columns]
    if absent:
        raise ValueError(f'Missing required columns: {absent}')
    missing_by_input = {kind: [c for c in required if c not in frame.columns] for kind, frame in active}
    if any(missing_by_input.values()):
        raise ValueError(f'Required columns missing in inputs: {missing_by_input}')
    for col in deduplicate_on or []:
        if col not in all_columns:
            raise ValueError(f'Duplicate-check column missing: {col}')
    # Reject contradictory non-null pandas dtype families before alignment.
    for col in all_columns:
        kinds = set()
        for _, frame in active:
            if col in frame and frame[col].notna().any():
                dtype = frame[col].dtype
                if pd.api.types.is_numeric_dtype(dtype):
                    kinds.add('numeric')
                elif pd.api.types.is_datetime64_any_dtype(dtype):
                    kinds.add('datetime')
                elif pd.api.types.is_bool_dtype(dtype):
                    kinds.add('boolean')
                else:
                    kinds.add('object')
        if len(kinds) > 1:
            raise ValueError(f'Incompatible dtype families for column {col}: {sorted(kinds)}')
    aligned = [frame.reindex(columns=all_columns).copy(deep=True) for _, frame in active]
    merged = pd.concat(aligned, ignore_index=True, sort=False)
    if id_column in merged:
        present = merged[id_column].map(lambda x: isinstance(x, str) and bool(x.strip()))
        invalid = merged[id_column].notna() & ~present
        if invalid.any():
            raise ValueError('Existing record IDs must be nonempty strings or missing')
        if merged.loc[present, id_column].duplicated().any():
            raise ValueError('Duplicate record IDs detected across inputs')
        missing_count = int((~present).sum())
    else:
        missing_count = len(merged)
    if missing_count:
        if not generate_missing_ids:
            raise ValueError('Missing record IDs and generate_missing_ids=False')
        merged = assign_record_ids(merged, id_column=id_column).dataframe
    if deduplicate_on and merged.duplicated(subset=deduplicate_on, keep=False).any():
        raise ValueError('Duplicate records found for deduplicate_on; resolve explicitly before merging')
    counts = merged['source_type'].value_counts().to_dict()
    warnings = []
    for col in all_columns:
        if any(col not in frame.columns for _, frame in active):
            warnings.append(f'Column {col} absent from at least one input; missing values introduced')
    return DatasetMergeResult(
        dataframe=merged,
        statistics={'total_records': len(merged), 'real_records': int(counts.get('real', 0)), 'synthetic_records': int(counts.get('synthetic', 0)), 'record_ids_generated': missing_count, 'columns': all_columns},
        transformations=[{'operation': 'merge_datasets', 'sources': [kind for kind, _ in active], 'input_rows': {kind: len(frame) for kind, frame in active}, 'rows_removed': 0}],
        warnings=warnings,
    )
