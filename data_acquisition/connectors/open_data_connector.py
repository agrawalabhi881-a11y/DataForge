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


class OpenDataConnector(BaseConnector):
    """
    Connector for querying open data APIs (such as CKAN package_search / package_show)
    and downloading publicly accessible dataset resources.
    """

    def __init__(
        self,
        base_url: str = "https://catalog.data.gov/api/3/action",
        output_dir: str = "data/raw/open_data",
    ):
        self.base_url = base_url.rstrip("/")
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
            self.logger.error(f"HTTP error {exc.code} requesting open data API ({url}): {exc.reason}")
            raise
        except URLError as exc:
            self.logger.error(f"Network error requesting open data API ({url}): {exc.reason}")
            raise

    def authenticate(self) -> bool:
        """
        Public open data portals typically do not require authentication for public catalog reads.
        """
        self.logger.info(f"OpenDataConnector initialized for endpoint: {self.base_url}")
        return True

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Searches a CKAN-compatible open data portal using `package_search`.
        """
        rows = max(1, min(max_results, 100))
        url = f"{self.base_url}/package_search?q={quote(query)}&rows={rows}"
        self.logger.info(f"Searching open data portal '{self.base_url}' for: '{query}'")

        try:
            data = self._request_json(url)
        except Exception as exc:
            self.logger.error(f"Open data search failed for '{query}': {exc}")
            return []

        result_block = data.get("result") if isinstance(data, dict) else {}
        packages = (result_block or {}).get("results", [])[:max_results]
        results: List[Dict[str, Any]] = []

        for pkg in packages:
            pkg_id = pkg.get("id") or pkg.get("name") or ""
            resources = pkg.get("resources") or []
            download_urls = [
                res.get("url")
                for res in resources
                if isinstance(res, dict) and res.get("url")
            ]
            formats = sorted(
                {
                    (res.get("format") or "").strip().lower()
                    for res in resources
                    if isinstance(res, dict) and (res.get("format") or "").strip()
                }
            )

            results.append(
                {
                    "dataset_id": pkg_id,
                    "name": pkg.get("title") or pkg.get("name") or pkg_id,
                    "platform": "OpenData",
                    "source_url": pkg.get("url") or f"{self.base_url}/package_show?id={quote(str(pkg_id))}",
                    "description": pkg.get("notes") or "",
                    "license": pkg.get("license_title") or pkg.get("license_id"),
                    "formats": formats,
                    "download_urls": download_urls,
                }
            )

        self.logger.info(f"Open data search returned {len(results)} dataset candidates.")
        return results

    def get_metadata(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves dataset metadata via `package_show` for a given package ID or slug.
        """
        if not dataset_id:
            self.logger.error("Empty dataset_id provided to OpenDataConnector.get_metadata.")
            return None

        url = f"{self.base_url}/package_show?id={quote(dataset_id)}"
        self.logger.info(f"Fetching open data metadata for '{dataset_id}'...")

        try:
            data = self._request_json(url)
        except Exception as exc:
            self.logger.error(f"Failed to fetch open data metadata for '{dataset_id}': {exc}")
            return None

        pkg = data.get("result") if isinstance(data, dict) else None
        if not isinstance(pkg, dict):
            self.logger.warning(f"No package metadata found for '{dataset_id}'.")
            return None

        resources_out: List[Dict[str, Any]] = []
        for res in pkg.get("resources") or []:
            if isinstance(res, dict):
                resources_out.append(
                    {
                        "id": res.get("id"),
                        "name": res.get("name"),
                        "format": (res.get("format") or "").strip().lower() or None,
                        "url": res.get("url"),
                        "size": res.get("size"),
                    }
                )

        return {
            "dataset_id": pkg.get("id") or pkg.get("name") or dataset_id,
            "name": pkg.get("title") or pkg.get("name") or dataset_id,
            "platform": "OpenData",
            "source_url": pkg.get("url") or url,
            "description": pkg.get("notes") or "",
            "license": pkg.get("license_title") or pkg.get("license_id"),
            "resources": resources_out,
        }

    def download(self, dataset_id: str, filename: Optional[str] = None) -> Optional[str]:
        """
        Downloads a resource file for `dataset_id`.
        If `dataset_id` starts with http:// or https://, downloads that direct URL;
        otherwise resolves resource URLs from `get_metadata(dataset_id)` and prefers
        tabular/structured formats (.csv, .json, .jsonl, .parquet, .tsv, .zip).
        """
        target_url: Optional[str] = None
        safe_folder = re.sub(r"[^A-Za-z0-9_.-]+", "_", dataset_id) or "open_data_item"

        if dataset_id.startswith(("http://", "https://")):
            target_url = dataset_id
        else:
            metadata = self.get_metadata(dataset_id)
            if not metadata:
                return None

            preferred_exts = (".csv", ".json", ".jsonl", ".parquet", ".tsv", ".zip")
            for res in metadata.get("resources") or []:
                res_url = res.get("url")
                if not res_url:
                    continue
                if filename and filename.lower() in res_url.lower():
                    target_url = res_url
                    break
                if any(res_url.lower().split("?")[0].endswith(ext) for ext in preferred_exts):
                    target_url = res_url
                    break

            if not target_url:
                for res in metadata.get("resources") or []:
                    if res.get("url"):
                        target_url = res["url"]
                        break

        if not target_url:
            self.logger.warning(f"No downloadable resource URL found for '{dataset_id}'.")
            return None

        resolved_url = urljoin(self.base_url + "/", target_url)
        target_dir = self.output_dir / safe_folder
        target_dir.mkdir(parents=True, exist_ok=True)

        raw_name = filename or Path(resolved_url.split("?")[0]).name or "dataset_resource"
        clean_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw_name)
        output_file = target_dir / clean_name

        self.logger.info(f"Downloading open data resource from '{resolved_url}' to '{output_file}'...")
        request = Request(resolved_url, headers=self._build_headers("*/*"))

        try:
            with urlopen(request, timeout=60) as response, open(output_file, "wb") as out_f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    out_f.write(chunk)

            self.logger.info(f"Successfully downloaded open data resource to: {output_file}")
            return str(output_file)
        except Exception as exc:
            self.logger.error(f"Failed to download open data resource '{resolved_url}': {exc}")
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