import os
import logging
from typing import Optional
from pathlib import Path
from data_acquisition.connectors.kaggle_connector import KaggleConnector
from data_acquisition.schemas.source_schema import DatasetMetadata

logger = logging.getLogger("IngestionService")

class IngestionService:
    """
    Orchestrates data retrieval, validation, and storage coordination 
    across multiple connectors in DataForge with robust path handling.
    """

    def __init__(self, base_storage_dir: Optional[str] = None):
        if base_storage_dir is None:
            # Dynamically resolve root-level 'data/raw' folder regardless of execution directory
            # services/ is at data_acquisition/services/, so go up 3 levels to project root (dataforge/)
            self.base_storage_dir = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
        else:
            self.base_storage_dir = Path(base_storage_dir)
            
        os.makedirs(self.base_storage_dir, exist_ok=True)
        logger.info(f"IngestionService initialized. Storage directory: {self.base_storage_dir}")

    def ingest_kaggle_dataset(self, dataset_ref: str, domain: str = "general") -> Optional[DatasetMetadata]:
        """
        Orchestrates downloading a Kaggle dataset and structuring its metadata 
        into our standard Pydantic schema.
        """
        connector = KaggleConnector()
        if not connector.authenticate():
            logger.error("Ingestion aborted: Kaggle authentication failed.")
            return None

        # Define robust output path for this dataset
        output_dir = self.base_storage_dir / "kaggle" / dataset_ref.replace("/", "_")
        
        try:
            # Download files
            downloaded_path = connector.download_data(dataset_ref, str(output_dir))
            
            # Construct standard metadata payload
            payload = {
                "dataset_id": dataset_ref,
                "source_platform": "Kaggle",
                "domain": domain,
                "title": dataset_ref.split("/")[-1],
                "file_path": str(downloaded_path),
                "extra_metadata": {"storage_type": "local_directory"}
            }

            # Validate using Pydantic schema
            metadata_obj = DatasetMetadata(**payload)
            logger.info(f"Successfully ingested and validated metadata for: {dataset_ref}")
            return metadata_obj

        except Exception as e:
            logger.error(f"Failed during ingestion pipeline for {dataset_ref}: {e}")
            return None