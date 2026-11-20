"""DataForge - Data Engineering: attack-log validation and ordering."""
from dataclasses import dataclass
import ipaddress
import pandas as pd

@dataclass
class AttackLogResult:
    dataframe: pd.DataFrame
    rejected_records: pd.DataFrame
    statistics: dict
    transformations: list[dict]

def process_attack_logs(dataframe: pd.DataFrame, timestamp_column: str = "timestamp") -> AttackLogResult:
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a Pandas DataFrame")
    if not dataframe.columns.is_unique or timestamp_column not in dataframe:
        raise ValueError("Unique columns and a timestamp column are required")
    out = dataframe.copy(deep=True)
    out["normalized_timestamp"] = pd.to_datetime(out[timestamp_column], errors="coerce", utc=True)
    reasons = [[] for _ in range(len(out))]
    for i, bad in enumerate(out["normalized_timestamp"].isna().to_numpy()):
        if bad: reasons[i].append("invalid_timestamp")
    for column in ("source_ip", "destination_ip"):
        if column in out:
            flags = []
            for i, value in enumerate(out[column]):
                try:
                    if pd.isna(value): raise ValueError("missing")
                    ipaddress.ip_address(str(value).strip())
                    flags.append(True)
                except ValueError:
                    flags.append(False)
                    reasons[i].append("invalid_" + column)
            out[column + "_valid"] = flags
    for column in ("source_port", "destination_port"):
        if column in out:
            nums = pd.to_numeric(out[column], errors="coerce")
            valid = nums.notna() & nums.between(0, 65535) & (nums % 1 == 0)
            out[column + "_valid"] = valid
            for i, ok in enumerate(valid.to_numpy()):
                if not ok: reasons[i].append("invalid_" + column)
    if "protocol" in out:
        out["normalized_protocol"] = out["protocol"].map(lambda v: v.strip().upper() if isinstance(v, str) else v)
    if "attack_stage" in out:
        out["normalized_attack_stage"] = out["attack_stage"].map(lambda v: v.strip().lower().replace("_", " ") if isinstance(v, str) else v)
    if "event_id" in out:
        out["duplicate_event"] = out["event_id"].notna() & out["event_id"].duplicated(keep=False)
    else:
        out["duplicate_event"] = out.duplicated(keep=False)
    out["rejection_reason"] = [";".join(r) if r else None for r in reasons]
    rejected = out.loc[out["rejection_reason"].notna()].copy()
    out = out.sort_values("normalized_timestamp", kind="stable", na_position="last").reset_index(drop=True)
    return AttackLogResult(out, rejected, {"total_records": len(out), "invalid_records": len(rejected), "duplicate_event_records": int(out["duplicate_event"].sum())}, [{"operation": "attack_log_validation_and_ordering", "rows_removed": 0, "session_id_policy": "preserve existing session IDs; do not infer sessions"}])
