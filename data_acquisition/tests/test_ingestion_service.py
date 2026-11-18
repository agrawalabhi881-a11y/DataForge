import sys
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path
from data_acquisition.services.ingestion_service import IngestionService

def test_ingestion_service_initialization(tmp_path):
    """Test that IngestionService initializes storage directory correctly."""
    custom_dir = tmp_path / "custom_data"
    service = IngestionService(base_storage_dir=str(custom_dir))
    assert service.base_storage_dir == custom_dir
    assert custom_dir.exists()

def test_ingest_kaggle_dataset_success(tmp_path):
    """Test full ingestion orchestration for a Kaggle dataset using mocks."""
    mock_kaggle = MagicMock()
    mock_api = MagicMock()
    mock_kaggle.api = mock_api
    mock_api.authenticate.return_value = True

    with patch.dict(sys.modules, {"kaggle": mock_kaggle}):
        service = IngestionService(base_storage_dir=str(tmp_path / "raw"))
        
        # Mock download_data to return a fake path
        with patch("data_acquisition.connectors.kaggle_connector.KaggleConnector.download_data") as mock_download:
            fake_download_path = str(tmp_path / "raw" / "kaggle" / "test_dataset")
            mock_download.return_value = fake_download_path
            
            metadata = service.ingest_kaggle_dataset("owner/test-dataset", domain="phishing")
            
            assert metadata is not None
            assert metadata.dataset_id == "owner/test-dataset"
            assert metadata.source_platform == "Kaggle"
            assert metadata.domain == "phishing"
            assert metadata.file_path == fake_download_path
            mock_download.assert_called_once()