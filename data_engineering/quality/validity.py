"""DataForge - Data Engineering: configurable field validity."""
import ipaddress
from urllib.parse import urlsplit
import pandas as pd


def _valid(value, kind):
    if pd.isna(value):
        return False
    try:
        if kind == "ip":
            ipaddress.ip_address(str(value)); return True
        if kind == "url":
            u = urlsplit(str(value)); return u.scheme.lower() in {"http", "https"} and bool(u.hostname) and ("." in u.hostname or u.hostname == "localhost")
        if kind == "timestamp":
            return not pd.isna(pd.to_datetime(value, errors="coerce", utc=True))
        if kind == "port":
            n = int(value); return str(value).strip() == str(n) and 0 <= n <= 65535
        if kind == "nonempty":
            return bool(str(value).strip())
    except (ValueError, TypeError, OverflowError):
        return False
    raise ValueError(f"Unsupported validity rule: {kind}")


def assess_validity(df: pd.DataFrame, rules: dict[str, str] | None = None) -> dict:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a DataFrame")
    if not df.columns.is_unique:
        raise ValueError("Duplicate column names")
    rules = {} if rules is None else rules
    if not isinstance(rules, dict):
        raise TypeError("rules must be a dictionary")
    supported = {"ip", "url", "timestamp", "port", "nonempty"}
    for col, kind in rules.items():
        if col not in df.columns:
            raise ValueError(f"Missing rule column: {col}")
        if kind not in supported:
            raise ValueError(f"Unsupported validity rule: {kind}")
    invalid = {col: int((~df[col].map(lambda x: _valid(x, kind))).sum()) for col, kind in rules.items()}
    total = len(df) * len(rules)
    return {"score": round(100 * (total - sum(invalid.values())) / total, 2) if total else 100.0,
            "invalid_by_column": invalid, "checked_cells": total}
