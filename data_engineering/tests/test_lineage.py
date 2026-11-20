"""Dataset version verification detects modified data."""
import pandas as pd
from data_engineering.lineage.lineage_tracker import LineageTracker
from data_engineering.lineage.dataset_versioning import create_dataset_version, verify_dataset_version


def test_lineage_version_and_integrity(tmp_path):
    frame = pd.DataFrame({"url": ["https://example.com"], "label": ["benign"]})
    tracker = LineageTracker(dataset_id="DF_TEST")
    tracker.add_source("SRC_001", raw_reference="storage/raw/phishing/source.csv")
    tracker.record("schema_transformation", configuration={"schema_version": "1.0"})
    manifest = create_dataset_version(frame, dataset_id="DF_TEST", version="1.0.0", lineage_fingerprint=tracker.fingerprint())
    assert verify_dataset_version(frame, manifest)
    modified = frame.copy()
    modified.loc[0, "label"] = "malicious"
    assert not verify_dataset_version(modified, manifest)
    path = tmp_path / "lineage.json"
    tracker.save_json(path)
    assert LineageTracker.load_json(path).to_dict() == tracker.to_dict()
