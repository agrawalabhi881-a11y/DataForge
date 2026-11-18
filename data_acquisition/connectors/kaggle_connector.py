import os
import logging
from typing import Dict, Any, List, Optional
from data_acquisition.connectors.base_connector import BaseConnector

logger = logging.getLogger(__name__)

class KaggleConnector(BaseConnector):
    """
    Kaggle API connector for searching and downloading datasets into DataForge.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api = None

    def authenticate(self) -> bool:
        """
        Authenticate using the Kaggle API.
        Expects kaggle.json credentials or environment variables KAGGLE_USERNAME and KAGGLE_KEY.
        """
        try:
            import kaggle
            kaggle.api.authenticate()
            self.api = kaggle.api
            self.logger.info("Successfully authenticated with Kaggle API.")
            return True
        except Exception as e:
            self.logger.error(f"Kaggle authentication failed: {e}")
            return False

    def fetch_datasets(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for datasets on Kaggle matching the query string.
        """
        if not self.api and not self.authenticate():
            self.logger.error("Cannot fetch datasets: Not authenticated.")
            return []

        try:
            self.logger.info(f"Searching Kaggle datasets for query: '{query}' (limit: {limit})")
            datasets = self.api.dataset_list(search=query, max_size=None)
            
            results = []
            for ds in datasets[:limit]:
                results.append({
                    "ref": ds.ref,
                    "title": ds.title,
                    "size": getattr(ds, 'totalSize', None),
                    "download_count": getattr(ds, 'downloadCount', None),
                })
            return results
        except Exception as e:
            self.logger.error(f"Failed to fetch datasets for query '{query}': {e}")
            return []

    def download_data(self, dataset_identifier: str, output_dir: str) -> str:
        """
        Download a specific Kaggle dataset (e.g., 'owner/dataset-name') 
        into the specified output directory. Returns the path to the downloaded files.
        """
        if not self.api and not self.authenticate():
            raise RuntimeError("Cannot download data: Kaggle authentication failed.")

        os.makedirs(output_dir, exist_ok=True)
        self.logger.info(f"Downloading dataset '{dataset_identifier}' to '{output_dir}'...")

        try:
            # Download and unzip dataset files into output_dir
            self.api.dataset_download_files(
                dataset=dataset_identifier, 
                path=output_dir, 
                unzip=True
            )
            self.logger.info(f"Successfully downloaded and extracted: {dataset_identifier}")
            return output_dir
        except Exception as e:
            self.logger.error(f"Error downloading dataset {dataset_identifier}: {e}")
            raise