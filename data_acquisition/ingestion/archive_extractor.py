import logging
import zipfile
import tarfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class ArchiveExtractor:
    """
    Handles safe extraction of compressed archives (.zip, .tar, .gz)
    downloaded from external data sources.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def extract_archive(self, archive_path: str, extract_to: str) -> Optional[str]:
        """
        Detects archive type and extracts its contents to the specified directory.
        """
        archive = Path(archive_path)
        output_dir = Path(extract_to)
        output_dir.mkdir(parents=True, exist_ok=True)

        if not archive.exists():
            self.logger.error(f"Archive not found at: {archive}")
            return None

        self.logger.info(f"Extracting archive {archive.name} to {output_dir}...")

        try:
            if zipfile.is_zipfile(archive):
                with zipfile.ZipFile(archive, 'r') as zip_ref:
                    zip_ref.extractall(output_dir)
                self.logger.info("ZIP archive extracted successfully.")
                return str(output_dir)
            
            elif tarfile.is_tarfile(archive):
                with tarfile.open(archive, 'r:*') as tar_ref:
                    tar_ref.extractall(output_dir)
                self.logger.info("TAR archive extracted successfully.")
                return str(output_dir)
            
            else:
                self.logger.warning(f"Unsupported archive format for file: {archive.name}")
                return None

        except Exception as e:
            self.logger.error(f"Failed to extract archive {archive.name}: {e}")
            raise