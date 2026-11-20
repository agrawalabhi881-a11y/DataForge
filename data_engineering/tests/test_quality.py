"""Quality metrics are derived from supplied records."""
import pandas as pd
from data_engineering.quality.quality_report import generate_quality_report


def test_quality_report_flags_invalid_values():
    frame = pd.DataFrame({"url": ["https://example.com", "bad", None], "label": ["benign", "malicious", "benign"], "source_ip": ["127.0.0.1", "bad", "1.1.1.1"]})
    report = generate_quality_report(frame, dataset_id="DF_TEST", domain="phishing", required_columns=["url", "label"], required_features=["url", "label", "timestamp"], validity_rules={"url": "url", "source_ip": "ip"}, allowed_values={"label": ["benign", "malicious"]})
    assert report["record_count"] == 3
    assert report["metrics"]["feature_coverage"]["score"] == 66.67
    assert report["metrics"]["validity"]["score"] < 100
    assert report["quality_status"] == "needs_improvement"
