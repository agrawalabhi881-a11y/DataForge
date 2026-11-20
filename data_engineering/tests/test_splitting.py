"""Dataset partitions are complete, reproducible and leakage-aware."""
import pandas as pd
from data_engineering.splitting.dataset_splitter import split_dataset, split_chronologically
from data_engineering.splitting.group_splitter import split_by_group


def _frame():
    return pd.DataFrame({"session_id": [f"S{i//3}" for i in range(30)], "label": ["benign", "malicious"] * 15, "timestamp": pd.date_range("2026-01-01", periods=30, freq="h")})


def test_random_split_reproducible():
    frame = _frame()
    first = split_dataset(frame, random_state=42)
    second = split_dataset(frame, random_state=42)
    assert len(first.train) + len(first.validation) + len(first.test) == len(frame)
    pd.testing.assert_frame_equal(first.train, second.train)


def test_group_split_no_leakage():
    result = split_by_group(_frame(), group_column="session_id", random_state=42)
    groups = [set(part["session_id"]) for part in (result.train, result.validation, result.test)]
    assert all(groups[i].isdisjoint(groups[j]) for i in range(3) for j in range(i+1, 3))


def test_chronological_order():
    result = split_chronologically(_frame(), timestamp_column="timestamp")
    assert result.train["timestamp"].max() < result.validation["timestamp"].min()
    assert result.validation["timestamp"].max() < result.test["timestamp"].min()
