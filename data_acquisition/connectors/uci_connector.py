import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

from data_acquisition.connectors.base_connector import BaseConnector

logger = logging.getLogger(__name__)


class UCIConnector(BaseConnector):
    """
    Connector for searching metadata and downloading publicly accessible datasets
    from the UCI Machine Learning Repository.
    """

    BASE_ARCHIVE_URL = "https://archive.ics.uci.edu"
    API_BASE_URL = "https://archive.ics.uci.edu/api"

    def __init__(self, output_dir: str = "data/raw/uci"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _build_headers(self, accept: str = "application/json") -> Dict[str, str]:
        return {
            "Accept": accept,
            "User-Agent": "DataForge-Acquisition-Engine/1.0",
        }

    def _request_json(self, url: str) -> Any:
        request = Request(url, headers=self._build_headers("application/json"))
        try:
            with urlopen(request, timeout=30) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload)
        except HTTPError as exc:
            self.logger.error(f"HTTP error {exc.code} requesting UCI endpoint ({url}): {exc.reason}")
            raise
        except URLError as exc:
            self.logger.error(f"Network error requesting UCI endpoint ({url}): {exc.reason}")
            raise

    def authenticate(self) -> bool:
        """UCI public repository endpoints do not require authentication credentials."""
        self.logger.info("UCIConnector initialized for public UCI repository access.")
        return True

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Searches UCI dataset metadata via its public API endpoint when available,
        returning normalized candidate entries.
        """
        self.logger.info(f"Searching UCI Machine Learning Repository for: '{query}'")
        endpoint = f"{self.API_BASE_URL}/datasets?search={quote(query)}"

        try:
            payload = self._request_json(endpoint)
        except Exception as exc:
            self.logger.warning(f"UCI search request failed for '{query}': {exc}")
            return []

        raw_items: List[Dict[str, Any]] = []
        if isinstance(payload, list):
            raw_items = payload
        elif isinstance(payload, dict):
            data_block = payload.get("data")
            if isinstance(data_block, list):
                raw_items = data_block
            elif isinstance(data_block, dict) and isinstance(data_block.get("datasets"), list):
                raw_items = data_block["datasets"]

        results: List[Dict[str, Any]] = []
        for item in raw_items[:max_results]:
            if not isinstance(item, dict):
                continue
            dataset_id = str(item.get("id") or item.get("slug") or item.get("name") or "")
            name = item.get("name") or item.get("title") or dataset_id
            results.append(
                {
                    "dataset_id": dataset_id,
                    "name": name,
                    "platform": "UCI",
                    "source_url": item.get("url")
                    or (f"{self.BASE_ARCHIVE_URL}/dataset/{dataset_id}" if dataset_id else self.BASE_ARCHIVE_URL),
                    "description": item.get("abstract") or item.get("description") or "",
                    "num_instances": item.get("num_instances"),
                    "num_features": item.get("num_features"),
                    "license": item.get("license"),
                }
            )

        self.logger.info(f"UCI search returned {len(results)} candidate datasets.")
        return results

    def get_metadata(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves dataset metadata for a given UCI dataset ID or slug.
        """
        if not dataset_id:
            self.logger.error("Empty dataset_id provided to UCIConnector.get_metadata.")
            return None

        url = f"{self.API_BASE_URL}/dataset?id={quote(str(dataset_id))}"
        self.logger.info(f"Fetching UCI metadata for dataset_id='{dataset_id}'...")

        try:
            payload = self._request_json(url)
        except Exception as exc:
            self.logger.error(f"Failed to retrieve UCI metadata for '{dataset_id}': {exc}")
            return None

        record = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else payload
        if not isinstance(record, dict):
            self.logger.warning(f"Unexpected or empty metadata structure for UCI dataset '{dataset_id}'.")
            return None

        resolved_id = str(record.get("id") or dataset_id)
        return {
            "dataset_id": resolved_id,
            "name": record.get("name") or record.get("title") or resolved_id,
            "platform": "UCI",
            "source_url": record.get("url") or f"{self.BASE_ARCHIVE_URL}/dataset/{resolved_id}",
            "description": record.get("abstract") or record.get("description") or "",
            "area": record.get("area"),
            "task": record.get("task"),
            "num_instances": record.get("num_instances"),
            "num_features": record.get("num_features"),
            "features": record.get("features") or [],
            "target_col": record.get("target_col"),
            "license": record.get("license"),
            "data_url": record.get("data_url"),
        }

    def download(self, dataset_id: str, filename: Optional[str] = None) -> Optional[str]:
        """
        Downloads a UCI dataset from a direct HTTP(S) URL or from `data_url` in `get_metadata(dataset_id)`.
        """
        download_url: Optional[str] = None
        safe_folder = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(dataset_id)) or "uci_dataset"

        if str(dataset_id).startswith(("http://", "https://")):
            download_url = str(dataset_id)
        else:
            metadata = self.get_metadata(dataset_id)
            if metadata and isinstance(metadata.get("data_url"), str) and metadata["data_url"].strip():
                download_url = urljoin(self.BASE_ARCHIVE_URL + "/", metadata["data_url"].strip())

        if not download_url:
            self.logger.warning(
                f"No direct download URL available for UCI dataset '{dataset_id}'. "
                "Pass a direct file URL or ensure metadata provides a valid data_url."
            )
            return None

        target_dir = self.output_dir / safe_folder
        target_dir.mkdir(parents=True, exist_ok=True)

        raw_name = filename or Path(download_url.split("?")[0]).name or "data.csv"
        clean_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw_name)
        output_file = target_dir / clean_name

        self.logger.info(f"Downloading UCI dataset from '{download_url}' to '{output_file}'...")
        request = Request(download_url, headers=self._build_headers("*/*"))

        try:
            with urlopen(request, timeout=60) as response, open(output_file, "wb") as out_f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    out_f.write(chunk)

            self.logger.info(f"Successfully downloaded UCI file to: {output_file}")
            return str(output_file)
        except Exception as exc:
            self.logger.error(f"Failed to download UCI dataset from '{download_url}': {exc}")
            if output_file.exists():
                output_file.unlink(missing_ok=True)
            return None

    def download_dataset(self, dataset_ref: str, filename: Optional[str] = None) -> Optional[str]:
        """Compatibility wrapper matching earlier connector naming."""
        return self.download(dataset_id=dataset_ref, filename=filename)
    
    def fetch_datasets(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        return self.search(query=query, max_results=max_results)

    def download_data(self, dataset_id: str, filename: Optional[str] = None) -> Optional[str]:
        return self.download(dataset_id=dataset_id, filename=filename)