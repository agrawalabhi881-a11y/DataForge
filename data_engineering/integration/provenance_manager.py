"""DataForge - Data Engineering: explicit record-level provenance management."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import pandas as pd

SOURCE_TYPES = frozenset({'real', 'synthetic'})


@dataclass
class ProvenanceResult:
    dataframe: pd.DataFrame
    statistics: dict[str, Any]
    transformations: list[dict[str, Any]]


def validate_provenance(dataframe: pd.DataFrame) -> dict[str, Any]:
    """Report provenance errors without modifying records."""
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError('dataframe must be a pandas DataFrame')
    if not dataframe.columns.is_unique:
        raise ValueError('DataFrame column names must be unique')
    required = ('source_type', 'source_id', 'generation_method')
    missing = [c for c in required if c not in dataframe.columns]
    if missing:
        return {'valid': False, 'missing_columns': missing, 'invalid_row_positions': list(range(len(dataframe))), 'errors': [f'Missing provenance columns: {missing}']}
    errors = []
    invalid = []
    for pos, (_, row) in enumerate(dataframe.iterrows()):
        kind, sid, method = (row[c] for c in required)
        if not isinstance(kind, str) or kind not in SOURCE_TYPES:
            errors.append(f'Row {pos}: source_type must be real or synthetic')
            invalid.append(pos)
        elif kind == 'real':
            if not isinstance(sid, str) or not sid.strip():
                errors.append(f'Row {pos}: real record requires source_id')
                invalid.append(pos)
            if pd.notna(method):
                errors.append(f'Row {pos}: real record cannot have generation_method')
                invalid.append(pos)
        else:
            if not isinstance(method, str) or not method.strip():
                errors.append(f'Row {pos}: synthetic record requires generation_method')
                invalid.append(pos)
    return {'valid': not errors, 'missing_columns': [], 'invalid_row_positions': sorted(set(invalid)), 'errors': errors}


def attach_provenance(
    dataframe: pd.DataFrame,
    *,
    source_type: str,
    source_id: str | None = None,
    generation_method: str | None = None,
    overwrite: bool = False,
) -> ProvenanceResult:
    """Attach explicit provenance; existing fields are protected by default."""
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError('dataframe must be a pandas DataFrame')
    if not dataframe.columns.is_unique:
        raise ValueError('DataFrame column names must be unique')
    if source_type not in SOURCE_TYPES:
        raise ValueError('source_type must be real or synthetic')
    if source_type == 'real':
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError('real records require a nonempty source_id')
        if generation_method is not None:
            raise ValueError('real records cannot have generation_method')
    else:
        if not isinstance(generation_method, str) or not generation_method.strip():
            raise ValueError('synthetic records require a nonempty generation_method')
    fields = {'source_type': source_type, 'source_id': source_id, 'generation_method': generation_method}
    result = dataframe.copy(deep=True)
    existing = [key for key in fields if key in result.columns]
    if existing and not overwrite:
        raise ValueError(f'Existing provenance columns cannot be overwritten: {existing}')
    for key, value in fields.items():
        result[key] = value
    return ProvenanceResult(
        dataframe=result,
        statistics={'record_count': len(result), 'source_type': source_type, 'source_id': source_id, 'generation_method': generation_method},
        transformations=[{'operation': 'attach_provenance', 'columns': list(fields), 'overwrite': overwrite}],
    )
