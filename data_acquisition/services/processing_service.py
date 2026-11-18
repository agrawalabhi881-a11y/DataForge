import logging
import pandas as pd
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class ProcessingService:
    """
    Orchestrates the cleaning, transformation, and storage of raw datasets
    into processed formats ready for modeling.
    """

    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw"
        self.processed_dir = self.base_dir / "processed"
        
        # Ensure both directories exist on initialization
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(self.__class__.__name__)

    def process_csv_dataset(self, dataset_name: str, filename: str) -> Optional[str]:
        """
        Reads a raw CSV file, cleans it, and writes it to the processed directory.
        """
        raw_file_path = self.raw_dir / "kaggle" / dataset_name / filename
        
        if not raw_file_path.exists():
            self.logger.error(f"Raw file not found at: {raw_file_path}")
            return None

        self.logger.info(f"Processing raw dataset from: {raw_file_path}")
        
        try:
            df = pd.read_csv(raw_file_path)
            
            initial_count = len(df)
            df = df.drop_duplicates()
            df = df.dropna()
            self.logger.info(f"Cleaned dataset: dropped {initial_count - len(df)} rows.")

            output_path = self.processed_dir / f"{dataset_name}_processed.csv"
            df.to_csv(output_path, index=False)
            
            self.logger.info(f"Successfully saved processed dataset to: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Failed to process dataset {dataset_name}: {e}")
            raise