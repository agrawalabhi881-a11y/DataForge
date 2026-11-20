"""DataForge - Data Engineering: phishing URL feature preparation."""
from dataclasses import dataclass
from urllib.parse import urlsplit
import math
import re
import pandas as pd

@dataclass
class PhishingResult:
    dataframe: pd.DataFrame
    rejected_records: pd.DataFrame
    statistics: dict
    transformations: list[dict]

def process_phishing(dataframe: pd.DataFrame, url_column: str = "url", label_column: str = "label") -> PhishingResult:
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a Pandas DataFrame")
    if not dataframe.columns.is_unique or url_column not in dataframe:
        raise ValueError("Unique columns and the URL column are required")
    result = dataframe.copy(deep=True)
    result["original_url"] = result[url_column]
    reasons = []
    domains, subdomains, tlds, depths, https, entropy, normalized = [], [], [], [], [], [], []
    for value in result[url_column]:
        reason = None
        host = ""
        url = value if isinstance(value, str) else ""
        url = url.strip()
        try:
            parsed = urlsplit(url)
            host = (parsed.hostname or "").lower()
            if parsed.scheme.lower() not in {"http", "https"} or not host or any(c.isspace() for c in host):
                reason = "invalid_http_url"
            if host and ("." not in host or host.startswith(".") or host.endswith(".")):
                reason = "invalid_hostname"
            _ = parsed.port
        except ValueError:
            reason = "malformed_url"
            parsed = urlsplit("")
        labels = host.split(".") if host else []
        domains.append(host if reason is None else pd.NA)
        tlds.append(labels[-1] if len(labels) > 1 and reason is None else pd.NA)
        subdomains.append(max(0, len(labels)-2) if reason is None else pd.NA)
        depths.append(len([x for x in parsed.path.split("/") if x]) if reason is None else pd.NA)
        https.append(parsed.scheme.lower() == "https" if reason is None else pd.NA)
        normalized.append(url if reason is None else pd.NA)
        if url:
            entropy.append(-sum((url.count(ch)/len(url))*math.log2(url.count(ch)/len(url)) for ch in set(url)))
        else:
            entropy.append(pd.NA)
        reasons.append(reason)
    result["normalized_url"] = normalized
    result["domain"] = domains
    result["top_level_domain"] = tlds
    result["subdomain_count"] = subdomains
    result["path_depth"] = depths
    result["https"] = https
    result["url_length"] = [len(v) if isinstance(v, str) else pd.NA for v in normalized]
    result["domain_length"] = [len(v) if isinstance(v, str) else pd.NA for v in domains]
    result["entropy"] = entropy
    result["suspicious_pattern_flag"] = [bool(re.search(r"@|%00|\b(login|verify|password)\b", v, re.I)) if isinstance(v, str) else False for v in normalized]
    result["duplicate_url"] = result["normalized_url"].notna() & result["normalized_url"].duplicated(keep=False)
    result["rejection_reason"] = reasons
    if label_column in result:
        result["normalized_label"] = result[label_column].map(lambda x: x.strip().lower() if isinstance(x, str) else x)
    rejected = result.loc[result["rejection_reason"].notna()].copy()
    return PhishingResult(result, rejected, {"total_records": len(result), "invalid_urls": len(rejected), "duplicate_url_records": int(result["duplicate_url"].sum())}, [{"operation": "phishing_feature_extraction", "rows_removed": 0, "warning": "Suspicious patterns are indicators, not verified maliciousness"}])
