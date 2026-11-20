"""DataForge - Data Engineering: vulnerability dataset validation."""
from dataclasses import dataclass
import re
import pandas as pd

@dataclass
class VulnerableCodeResult:
    dataframe: pd.DataFrame
    rejected_records: pd.DataFrame
    statistics: dict
    transformations: list[dict]

def process_vulnerable_code(dataframe: pd.DataFrame, code_column: str = "code_snippet") -> VulnerableCodeResult:
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a Pandas DataFrame")
    if not dataframe.columns.is_unique or code_column not in dataframe:
        raise ValueError("Unique columns and code_snippet column are required")
    out = dataframe.copy(deep=True)
    reasons = [[] for _ in range(len(out))]
    lengths = []
    for i, value in enumerate(out[code_column]):
        if not isinstance(value, str) or not value.strip():
            reasons[i].append("missing_code")
            lengths.append(0)
        else:
            lengths.append(len(value.splitlines()))
    out["code_line_count"] = lengths
    out["duplicate_code"] = out[code_column].notna() & out[code_column].duplicated(keep=False)
    if "programming_language" in out:
        out["normalized_language"] = out["programming_language"].map(lambda x: x.strip().lower() if isinstance(x, str) else x)
    if "vulnerability_type" in out:
        out["normalized_vulnerability_type"] = out["vulnerability_type"].map(lambda x: x.strip().lower() if isinstance(x, str) else x)
    if "cwe_id" in out:
        normalized_cwe = []
        for i, value in enumerate(out["cwe_id"]):
            if pd.isna(value) or str(value).strip() == "":
                normalized_cwe.append(pd.NA)
                continue
            match = re.fullmatch(r"(?:CWE[-_ ]?)?(\d+)", str(value).strip(), re.I)
            if not match or int(match.group(1)) <= 0:
                reasons[i].append("invalid_cwe_id")
                normalized_cwe.append(pd.NA)
            else:
                normalized_cwe.append("CWE-" + str(int(match.group(1))))
        out["normalized_cwe_id"] = normalized_cwe
    if "vulnerable_lines" in out:
        for i, value in enumerate(out["vulnerable_lines"]):
            if value is None or value is pd.NA:
                continue
            if isinstance(value, (list, tuple)):
                lines = value
            elif isinstance(value, str) and value.strip():
                try: lines = [int(x.strip()) for x in value.split(",")]
                except ValueError: lines = [0]
            elif pd.isna(value):
                continue
            else:
                lines = [value]
            if any(isinstance(x, bool) or not isinstance(x, int) or x < 1 or x > lengths[i] for x in lines):
                reasons[i].append("invalid_vulnerable_lines")
    if "label" in out:
        out["normalized_label"] = out["label"].map(lambda x: x.strip().lower() if isinstance(x, str) else x)
    out["rejection_reason"] = [";".join(r) if r else None for r in reasons]
    rejected = out.loc[out["rejection_reason"].notna()].copy()
    return VulnerableCodeResult(out, rejected, {"total_records": len(out), "invalid_records": len(rejected), "duplicate_code_records": int(out["duplicate_code"].sum())}, [{"operation": "code_validation", "rows_removed": 0, "code_formatting_preserved": True}])
