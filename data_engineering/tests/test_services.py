"""Service layer composes operations without modifying input records."""
import pandas as pd
from data_engineering.services.processing_service import ProcessingStep, process_dataset
from data_engineering.services.quality_service import assess_dataset_quality


def test_processing_and_quality_service():
    frame = pd.DataFrame({"url": [" https://example.com "], "label": ["benign"]})
    result = process_dataset(frame, steps=[ProcessingStep(name="strip_url", operation=lambda df: df.assign(url=df["url"].str.strip()))], dataset_id="DF_TEST", domain="phishing")
    assert result.dataframe.loc[0, "url"] == "https://example.com"
    assert frame.loc[0, "url"] == " https://example.com "
    assert result.metadata["steps_executed"] == 1
    quality = assess_dataset_quality(result.dataframe, dataset_id="DF_TEST", domain="phishing", required_columns=["url", "label"], required_features=["url", "label"])
    assert isinstance(quality.report, dict)
    assert quality.report["record_count"] == 1
