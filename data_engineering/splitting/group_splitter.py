"""DataForge - Data Engineering: group-isolated train/validation/test splits."""
from collections.abc import Sequence
import numpy as np
import pandas as pd
from .dataset_splitter import SplitResult, _check_frame, validate_ratios


def split_by_group(dataframe: pd.DataFrame, group_column: str, train_size: float = 0.7, validation_size: float = 0.15, test_size: float = 0.15, random_state: int = 42) -> SplitResult:
    """Assign whole groups to one split; approximate row ratios without leakage."""
    _check_frame(dataframe)
    validate_ratios(train_size, validation_size, test_size)
    if group_column not in dataframe:
        raise ValueError(f'Group column not found: {group_column}')
    if dataframe[group_column].isna().any():
        raise ValueError('Missing group identifiers cannot be safely split.')
    if isinstance(random_state, bool) or not isinstance(random_state, int):
        raise TypeError('random_state must be an integer.')
    codes, groups = pd.factorize(dataframe[group_column], sort=False)
    if len(groups) < 3:
        raise ValueError('At least three distinct groups are required.')
    counts = np.bincount(codes)
    rng = np.random.default_rng(random_state)
    order = rng.permutation(len(groups))
    order = sorted(order, key=lambda i: -counts[i])
    targets = np.array([train_size, validation_size, test_size]) * len(dataframe)
    assigned = np.full(len(groups), -1, dtype=int)
    loads = np.zeros(3, dtype=int)
    # Seed every partition to guarantee nonempty splits.
    for split_idx, group_idx in enumerate(order[:3]):
        assigned[group_idx] = split_idx
        loads[split_idx] += counts[group_idx]
    for group_idx in order[3:]:
        deficit = targets - loads
        split_idx = int(np.argmax(deficit))
        assigned[group_idx] = split_idx
        loads[split_idx] += counts[group_idx]
    partitions = [dataframe.iloc[np.flatnonzero(assigned[codes] == i)].copy() for i in range(3)]
    return SplitResult(*partitions, statistics={
        'method': 'group', 'group_column': group_column, 'random_state': random_state,
        'total_records': len(dataframe), 'total_groups': len(groups),
        'train_records': len(partitions[0]), 'validation_records': len(partitions[1]), 'test_records': len(partitions[2]),
        'train_groups': int((assigned == 0).sum()), 'validation_groups': int((assigned == 1).sum()), 'test_groups': int((assigned == 2).sum()),
    })
