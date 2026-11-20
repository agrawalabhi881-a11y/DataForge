"""DataForge - Data Engineering: user activity sequence validation."""
from dataclasses import dataclass
import pandas as pd

@dataclass
class UserBehaviorResult:
    dataframe: pd.DataFrame
    rejected_records: pd.DataFrame
    statistics: dict
    transformations: list[dict]

def process_user_behavior(dataframe: pd.DataFrame, timestamp_column: str = "timestamp", user_column: str = "user_id") -> UserBehaviorResult:
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a Pandas DataFrame")
    if not dataframe.columns.is_unique or timestamp_column not in dataframe or user_column not in dataframe:
        raise ValueError("Unique columns, timestamp, and user_id are required")
    out = dataframe.copy(deep=True)
    out["normalized_timestamp"] = pd.to_datetime(out[timestamp_column], errors="coerce", utc=True)
    reasons = []
    for user, timestamp in zip(out[user_column], out["normalized_timestamp"]):
        errors = []
        if pd.isna(user) or (isinstance(user, str) and not user.strip()):
            errors.append("missing_user_id")
        if pd.isna(timestamp): errors.append("invalid_timestamp")
        reasons.append(";".join(errors) if errors else None)
    if "activity_type" in out:
        out["normalized_activity"] = out["activity_type"].map(lambda x: x.strip().lower() if isinstance(x, str) else x)
    keys = [c for c in ("event_id",) if c in out]
    if not keys:
        keys = [c for c in (user_column, "session_id", timestamp_column, "activity_type") if c in out]
    out["duplicate_activity"] = out.duplicated(subset=keys, keep=False)
    out["rejection_reason"] = reasons
    rejected = out.loc[out["rejection_reason"].notna()].copy()
    sort_columns = [user_column]
    if "session_id" in out: sort_columns.append("session_id")
    sort_columns.append("normalized_timestamp")
    out = out.sort_values(sort_columns, kind="stable", na_position="last").reset_index(drop=True)
    if "session_id" in out:
        out["session_event_order"] = out.groupby([user_column, "session_id"], dropna=False).cumcount() + 1
    else:
        out["session_event_order"] = pd.NA
    return UserBehaviorResult(out, rejected, {"total_records": len(out), "invalid_records": len(rejected), "duplicate_activity_records": int(out["duplicate_activity"].sum())}, [{"operation": "user_behavior_validation_and_ordering", "rows_removed": 0, "session_policy": "preserve supplied IDs; do not infer identity or sessions", "privacy_note": "Check source privacy terms before sharing user identifiers"}])
