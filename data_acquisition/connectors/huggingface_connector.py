import logging
from pathlib import Path
from typing import Optional
from data_acquisition.connectors.base_connector import BaseConnector

logger = logging.getLogger(__name__)

class HuggingFaceConnector(BaseConnector):
    """
    Connector for fetching tabular datasets from the Hugging Face Hub.
    Inherits from BaseConnector to maintain a uniform interface.
    """

    def __init__(self, output_dir: str = "data/raw/huggingface"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)

    def authenticate(self) -> bool:
        """
        Hugging Face public datasets do not strictly require API tokens for downloading,
        though token authentication can be added via environment variables if needed.
        """
        self.logger.info("Hugging Face Connector initialized for public datasets.")
        return True

    def download_dataset(self, dataset_ref: str, filename: Optional[str] = None) -> Optional[str]:
        """
        Downloads a dataset from Hugging Face and saves it as a local CSV file
        ready for downstream processing and modeling.
        """
        self.logger.info(f"Downloading dataset '{dataset_ref}' from Hugging Face...")
        
        try:
            from datasets import load_dataset
            
            # Load dataset from Hugging Face Hub
            dataset = load_dataset(dataset_ref)
            
            # Prepare target directory
            safe_name = dataset_ref.replace("/", "_")
            target_dir = self.output_dir / safe_name
            target_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = target_dir / (filename or "data.csv")
            
            # Convert train split (or first available split) to pandas DataFrame and save as CSV
            split_key = "train" if "train" in dataset else list(dataset.keys())[0]
            df = dataset[split_key].to_pandas()
            
            df.to_csv(output_file, index=False)
            self.logger.info(f"Successfully saved Hugging Face dataset to: {output_file}")
            
            return str(output_file)
            
        except ImportError:
            self.logger.error("The 'datasets' library is required for HuggingFaceConnector. Run 'pip install datasets'.")
            raise
        except Exception as e:
            self.logger.error(f"Failed to download Hugging Face dataset {dataset_ref}: {e}")
            return None