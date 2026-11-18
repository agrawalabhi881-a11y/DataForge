import logging
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)

class FileValidator:
    """
    Validates ingested raw files for structural integrity before processing.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def validate_csv(self, file_path: str, min_rows: int = 1) -> bool:
        """
        Validates that a CSV file exists, is non-empty, and can be parsed correctly.
        """
        path = Path(file_path)
        
        if not path.exists():
            self.logger.error(f"Validation failed: File does not exist at {path}")
            return False

        if path.stat().st_size == 0:
            self.logger.error(f"Validation failed: File is empty ({path.name})")
            return False

        try:
            # Quick sample read to verify parsing
            df = pd.read_csv(path, nrows=5)
            if len(df) < min_rows and path.stat().st_size > 10:
                self.logger.warning(f"File {path.name} has fewer than {min_rows} sample rows.")
            
            self.logger.info(f"File validation passed for: {path.name}")
            return True

        except Exception as e:
            self.logger.error(f"File validation failed for {path.name}: {e}")
            return False