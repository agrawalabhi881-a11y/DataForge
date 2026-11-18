import pytest
import pandas as pd
from pathlib import Path

from data_acquisition.data_discovery.deduplication import DatasetDeduplicator
from data_acquisition.data_discovery.metadata_extractor import MetadataExtractor
from data_acquisition.ingestion.file_validator import FileValidator
from data_acquisition.metadata.provenance import ProvenanceTracker
from data_acquisition.metadata.license_checker import LicenseChecker

def test_dataset_deduplicator():
    """Test deduplication logic across candidate dataset titles."""
    deduplicator = DatasetDeduplicator(similarity_threshold=0.8)
    candidates = [
        {"name": "Iris Dataset", "source": "kaggle"},
        {"name": "iris dataset", "source": "huggingface"}, # Should be detected as duplicate
        {"name": "Housing Prices", "source": "kaggle"}
    ]
    
    unique = deduplicator.deduplicate_sources(candidates)
    assert len(unique) == 2
    assert unique[0]["name"] == "Iris Dataset"
    assert unique[1]["name"] == "Housing Prices"

def test_metadata_extractor(tmp_path):
    """Test structural profiling of a CSV file."""
    csv_file = tmp_path / "sample.csv"
    df = pd.DataFrame({
        "feature_a": [1.0, 2.0, 3.0],
        "feature_b": ["x", "y", "z"]
    })
    df.to_csv(csv_file, index=False)

    extractor = MetadataExtractor()
    profile = extractor.extract_profile(str(csv_file))

    assert profile is not None
    assert profile["file_name"] == "sample.csv"
    assert "feature_a" in profile["columns"]
    assert "feature_b" in profile["columns"]

def test_file_validator(tmp_path):
    """Test file validation for existing non-empty CSV files."""
    valid_csv = tmp_path / "valid.csv"
    valid_csv.write_text("col1,col2\n1,2\n3,4")

    validator = FileValidator()
    assert validator.validate_csv(str(valid_csv)) is True

    # Test non-existent file
    assert validator.validate_csv(str(tmp_path / "nonexistent.csv")) is False

def test_provenance_tracker(tmp_path):
    """Test provenance record generation and file hashing."""
    test_file = tmp_path / "dataset.csv"
    test_file.write_text("id,val\n1,100")

    metadata_dir = tmp_path / "metadata"
    tracker = ProvenanceTracker(metadata_dir=str(metadata_dir))
    
    record_path = tracker.record_provenance(
        dataset_name="test/dataset",
        source_platform="kaggle",
        file_path=str(test_file)
    )

    assert Path(record_path).exists()

def test_license_checker():
    """Test license compliance verification."""
    checker = LicenseChecker(strict_mode=True)
    
    assert checker.is_license_compliant("mit") is True
    assert checker.is_license_compliant("apache-2.0") is True
    assert checker.is_license_compliant("proprietary-restricted") is False