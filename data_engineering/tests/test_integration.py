"""Provenance must be preserved across dataset merging."""
import pandas as pd
import pytest
from data_engineering.integration.provenance_manager import attach_provenance, validate_provenance
from data_engineering.integration.dataset_merger import merge_datasets


def test_merge_preserves_origin_and_source_frames():
    real = pd.DataFrame({"url": ["https://example.com"], "label": ["benign"]})
    synthetic = pd.DataFrame({"url": ["https://example.net"], "label": ["malicious"]})
    real_data = attach_provenance(real, source_type="real", source_id="SRC_001").dataframe
    synth_data = attach_provenance(synthetic, source_type="synthetic", generation_method="rule_based").dataframe
    merged = merge_datasets(real_data, synth_data, required_columns=["url", "label"])
    assert merged.statistics["total_records"] == 2
    assert merged.dataframe["record_id"].is_unique
    assert validate_provenance(merged.dataframe)["valid"]
    assert set(merged.dataframe["source_type"]) == {"real", "synthetic"}
    assert "source_type" not in real.columns
    assert "source_type" not in synthetic.columns


def test_merge_rejects_invalid_provenance():
    with pytest.raises(ValueError):
        merge_datasets(pd.DataFrame({"url": ["https://example.com"]}))
