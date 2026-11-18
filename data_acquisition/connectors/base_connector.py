import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseConnector(ABC):
    """
    Abstract Base Class for all data source connectors in DataForge.
    Defines the standard interface for authentication, searching, and downloading.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the target data platform."""
        pass

    @abstractmethod
    def fetch_datasets(self, query: str, limit: int = 10) -> list:
        """Fetch datasets or records matching the query."""
        pass

    @abstractmethod
    def download_data(self, dataset_identifier: str, output_dir: str) -> str:
        """Download dataset files to the specified output directory."""
        pass