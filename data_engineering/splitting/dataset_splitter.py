"""DataForge - Data Engineering: reproducible row and chronological splits."""
from dataclasses import dataclass
from typing import Any
import pandas as pd
import numpy as np


@dataclass
class SplitResult:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame
    statistics: dict[str, Any]


def validate_ratios(train_size: float, validation_size: float, test_size: float) -> None:
    sizes = (train_size, validation_size, test_size)
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not np.isfinite(x) or x <= 0 for x in sizes):
        raise ValueError('All split ratios must be positive finite numbers.')
    if not np.isclose(sum(sizes), 1.0, atol=1e-9):
        raise ValueError('Split ratios must sum to 1.')


def _check_frame(df: pd.DataFrame) -> None:
    if not isinstance(df, pd.DataFrame):
        raise TypeError('dataframe must be a Pandas DataFrame.')
    if not df.columns.is_unique:
        raise ValueError('Column names must be unique.')
    if len(df) < 3:
        raise ValueError('At least three records are required.')


def _sizes(n: int, ratios: tuple[float, float, float]) -> tuple[int, int, int]:
    raw = np.array(ratios) * n
    counts = np.floor(raw).astype(int)
    for i in np.argsort(-(raw - counts), kind='stable')[:n - int(counts.sum())]:
        counts[i] += 1
    if any(counts == 0):
        raise ValueError('Insufficient records for non-empty train/validation/test splits.')
    return tuple(int(x) for x in counts)


def _assemble(df: pd.DataFrame, positions: np.ndarray, counts: tuple[int, int, int], method: str, seed: int | None) -> SplitResult:
    a, b, _ = counts
    parts = [df.iloc[positions[:a]].copy(), df.iloc[positions[a:a+b]].copy(), df.iloc[positions[a+b:]].copy()]
    return SplitResult(*parts, statistics={'method': method, 'random_state': seed, 'total_records': len(df), 'train_records': len(parts[0]), 'validation_records': len(parts[1]), 'test_records': len(parts[2])})


def split_dataset(dataframe: pd.DataFrame, train_size: float = 0.7, validation_size: float = 0.15, test_size: float = 0.15, random_state: int = 42, stratify_column: str | None = None) -> SplitResult:
    """Random split; optional stratification maintains class proportions when feasible."""
    _check_frame(dataframe)
    validate_ratios(train_size, validation_size, test_size)
    if isinstance(random_state, bool) or not isinstance(random_state, int):
        raise TypeError('random_state must be an integer.')
    counts = _sizes(len(dataframe), (train_size, validation_size, test_size))
    if stratify_column is None:
        positions = np.random.default_rng(random_state).permutation(len(dataframe))
        return _assemble(dataframe, positions, counts, 'random', random_state)
    if stratify_column not in dataframe:
        raise ValueError(f'Stratification column not found: {stratify_column}')
    from sklearn.model_selection import train_test_split
    try:
        idx = np.arange(len(dataframe))
        train_idx, hold_idx = train_test_split(idx, train_size=counts[0], test_size=counts[1]+counts[2], stratify=dataframe[stratify_column], random_state=random_state)
        val_idx, test_idx = train_test_split(hold_idx, train_size=counts[1], test_size=counts[2], stratify=dataframe.iloc[hold_idx][stratify_column], random_state=random_state)
    except ValueError as exc:
        raise ValueError(f'Stratification cannot preserve classes with these data and ratios: {exc}') from exc
    positions = np.concatenate([train_idx, val_idx, test_idx])
    return _assemble(dataframe, positions, counts, 'stratified', random_state)


def split_chronologically(dataframe: pd.DataFrame, timestamp_column: str, train_size: float = 0.7, validation_size: float = 0.15, test_size: float = 0.15) -> SplitResult:
    """Chronological split; rejects invalid timestamps and tied timestamps across boundaries."""
    _check_frame(dataframe)
    validate_ratios(train_size, validation_size, test_size)
    if timestamp_column not in dataframe:
        raise ValueError(f'Timestamp column not found: {timestamp_column}')
    timestamps = pd.to_datetime(dataframe[timestamp_column], errors='coerce', utc=True)
    if timestamps.isna().any():
        raise ValueError('Timestamp column contains missing or invalid values.')
    counts = _sizes(len(dataframe), (train_size, validation_size, test_size))
    positions = np.argsort(timestamps.to_numpy(), kind='stable')
    a, b, _ = counts
    ordered = timestamps.iloc[positions].reset_index(drop=True)
    if ordered.iloc[a-1] == ordered.iloc[a] or ordered.iloc[a+b-1] == ordered.iloc[a+b]:
        raise ValueError('Identical timestamps cross split boundaries; adjust ratios or use grouped splitting.')
    return _assemble(dataframe, positions, counts, 'chronological', None)
