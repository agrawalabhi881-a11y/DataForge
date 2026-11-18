import logging
from pathlib import Path
import pandas as pd
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MetadataExtractor:
    """
    Extracts structural profiles and statistical metadata from discovered raw data files.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def extract_profile(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Reads a sample of a data file and extracts column types, row counts, and null counts.
        """
        path = Path(file_path)
        if not path.exists():
            self.logger.error(f"Cannot extract profile: File not found at {path}")
            return None

        self.logger.info(f"Extracting structural profile for: {path.name}")

        try:
            # Read header and sample rows
            df = pd.read_csv(path, nrows=1000)
            total_rows = sum(1 for _ in open(path, encoding="utf-8", errors="ignore")) - 1 # approximate row count excluding header

            profile = {
                "file_name": path.name,
                "estimated_rows": max(total_rows, 0),
                "columns": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "missing_values_sample": df.isnull().sum().to_dict()
            }

            self.logger.info(f"Successfully profiled {path.name}: {len(profile['columns'])} columns detected.")
            return profile

        except Exception as e:
            self.logger.error(f"Failed to extract metadata profile for {path.name}: {e}")
            return None