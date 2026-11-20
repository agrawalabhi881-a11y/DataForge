"""DataForge - Data Engineering: deterministic sequential record identifiers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
import re
import pandas as pd


@dataclass
class RecordIDResult:
    dataframe: pd.DataFrame
    statistics: dict[str, Any]
    transformations: list[dict[str, Any]]


def generate_record_ids(count: int, *, prefix: str = 'REC', start: int = 1, width: int = 6, existing_ids: Iterable[str] = ()) -> list[str]:
    """Generate IDs avoiding supplied existing IDs; caller must coordinate concurrent writers."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError('count must be a nonnegative integer')
    if not isinstance(prefix, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', prefix):
        raise ValueError('prefix must contain only letters, digits and underscores and start with a letter')
    if isinstance(start, bool) or not isinstance(start, int) or start < 0:
        raise ValueError('start must be a nonnegative integer')
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise ValueError('width must be a positive integer')
    reserved = set(existing_ids)
    generated = []
    number = start
    while len(generated) < count:
        candidate = f'{prefix}_{number:0{width}d}'
        if candidate not in reserved:
            generated.append(candidate)
            reserved.add(candidate)
        number += 1
    return generated


def assign_record_ids(
    dataframe: pd.DataFrame, *, id_column: str = 'record_id', prefix: str = 'REC',
    start: int = 1, width: int = 6, existing_ids: Iterable[str] = (),
    preserve_existing: bool = True,
) -> RecordIDResult:
    """Assign missing IDs, rejecting duplicate IDs and collisions."""
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError('dataframe must be a pandas DataFrame')
    if not dataframe.columns.is_unique:
        raise ValueError('DataFrame column names must be unique')
    if not isinstance(id_column, str) or not id_column:
        raise ValueError('id_column must be a nonempty string')
    result = dataframe.copy(deep=True)
    reserved = set(existing_ids)
    if id_column in result.columns and preserve_existing:
        existing = result[id_column]
        present = existing.map(lambda x: isinstance(x, str) and bool(x.strip()))
        invalid = existing.notna() & ~present
        if invalid.any():
            raise ValueError('Existing record IDs must be nonempty strings or missing')
        values = existing[present].tolist()
        if len(values) != len(set(values)):
            raise ValueError('Existing record IDs contain duplicates')
        if set(values) & reserved:
            raise ValueError('Existing record IDs collide with reserved IDs')
        reserved.update(values)
        missing_positions = [i for i, is_present in enumerate(present.tolist()) if not is_present]
    else:
        missing_positions = list(range(len(result)))
    generated = generate_record_ids(len(missing_positions), prefix=prefix, start=start, width=width, existing_ids=reserved)
    if id_column not in result.columns or not preserve_existing:
        result[id_column] = pd.Series([None] * len(result), index=result.index, dtype='object')
    column_pos = result.columns.get_loc(id_column)
    for pos, identifier in zip(missing_positions, generated):
        result.iat[pos, column_pos] = identifier
    return RecordIDResult(result, {'record_count': len(result), 'ids_generated': len(generated), 'ids_preserved': len(result) - len(generated)}, [{'operation': 'assign_record_ids', 'id_column': id_column, 'generated': len(generated), 'preserve_existing': preserve_existing}])
