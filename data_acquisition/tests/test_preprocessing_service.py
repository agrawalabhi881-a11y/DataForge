import pandas as pd
import pytest
from pathlib import Path
from data_acquisition.services.processing_service import ProcessingService

def test_processing_service_initialization(tmp_path):
    """Test that ProcessingService sets up processed directory correctly."""
    service = ProcessingService(base_dir=str(tmp_path))
    assert service.processed_dir.exists()
    assert service.raw_dir.exists()

def test_process_csv_dataset_success(tmp_path):
    """Test cleaning and processing of a raw CSV dataset."""
    # Setup raw directory structure and a mock raw CSV file
    raw_kaggle_dir = tmp_path / "raw" / "kaggle" / "test_dataset"
    raw_kaggle_dir.mkdir(parents=True, exist_ok=True)
    
    raw_file = raw_kaggle_dir / "data.csv"
    
    # Create sample dataframe with duplicates and missing values to test cleaning
    df_raw = pd.DataFrame({
        "col1": [1, 2, 2, None, 4],
        "col2": ["a", "b", "b", "c", "d"]
    })
    df_raw.to_csv(raw_file, index=False)

    # Initialize service pointing to temp dir
    service = ProcessingService(base_dir=str(tmp_path))
    
    # Run processing
    processed_path_str = service.process_csv_dataset(dataset_name="test_dataset", filename="data.csv")
    
    assert processed_path_str is not None
    processed_path = Path(processed_path_str)
    assert processed_path.exists()

    # Verify cleaning results (dropped missing row and duplicate row)
    df_processed = pd.read_csv(processed_path)
    # Original: 5 rows -> 1 missing removed (4 left) -> 1 duplicate removed (3 left)
    assert len(df_processed) == 3
    assert df_processed.isnull().sum().sum() == 0