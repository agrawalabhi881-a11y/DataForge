import sys
from unittest.mock import MagicMock, patch
import pytest
from data_acquisition.schemas.source_schema import DatasetMetadata
from data_acquisition.connectors.kaggle_connector import KaggleConnector

def test_kaggle_connector_initialization():
    """Test that KaggleConnector initializes correctly with config."""
    config = {"api_key": "test_key"}
    connector = KaggleConnector(config=config)
    assert connector.config == config
    assert connector.api is None

def test_kaggle_authentication_success():
    """Test successful authentication with Kaggle using a mocked module."""
    mock_kaggle = MagicMock()
    mock_api = MagicMock()
    mock_api.authenticate.return_value = True
    mock_kaggle.api = mock_api

    with patch.dict(sys.modules, {"kaggle": mock_kaggle}):
        connector = KaggleConnector()
        result = connector.authenticate()
        
        assert result is True
        mock_api.authenticate.assert_called_once()

def test_kaggle_download_data(tmp_path):
    """Test downloading datasets through KaggleConnector with a mocked module."""
    mock_kaggle = MagicMock()
    mock_api = MagicMock()
    mock_kaggle.api = mock_api

    with patch.dict(sys.modules, {"kaggle": mock_kaggle}):
        connector = KaggleConnector()
        connector.api = mock_api
        
        output_dir = tmp_path / "test_download"
        result_path = connector.download_data("owner/test-dataset", str(output_dir))
        
        mock_api.dataset_download_files.assert_called_once_with(
            dataset="owner/test-dataset",
            path=str(output_dir),
            unzip=True
        )
        assert result_path == str(output_dir)

def test_dataset_metadata_validation():
    """Test Pydantic schema validation for ingested datasets."""
    payload = {
        "dataset_id": "test/dataset",
        "source_platform": "Kaggle",
        "domain": "phishing",
        "title": "Test Dataset",
        "record_count": 1000
    }
    metadata = DatasetMetadata(**payload)
    assert metadata.dataset_id == "test/dataset"
    assert metadata.source_platform == "Kaggle"
    assert metadata.record_count == 1000
    assert metadata.version == "1.0.0"