import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from data_acquisition.connectors.base_connector import BaseConnector

logger = logging.getLogger(__name__)


class GitHubConnector(BaseConnector):
    """
    Connector for searching and downloading eligible dataset files from public GitHub repositories.
    Uses the GitHub REST API v3 and optional GITHUB_TOKEN authentication.
    """

    API_BASE_URL = "https://api.github.com"

    def __init__(self, output_dir: str = "data/raw/github", token: Optional[str] = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.logger = logging.getLogger(self.__class__.__name__)

    def _build_headers(self, accept: str = "application/vnd.github+json") -> Dict[str, str]:
        headers = {
            "Accept": accept,
            "User-Agent": "DataForge-Acquisition-Engine/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request_json(self, url: str) -> Any:
        request = Request(url, headers=self._build_headers())
        try:
            with urlopen(request, timeout=30) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload)
        except HTTPError as exc:
            if exc.code == 403:
                self.logger.warning(
                    "GitHub API rate limit or access restriction encountered (HTTP 403). "
                    "Set GITHUB_TOKEN to increase rate limits."
                )
            elif exc.code == 404:
                self.logger.warning(f"GitHub resource not found (HTTP 404): {url}")
            else:
                self.logger.error(f"GitHub HTTP error {exc.code} for {url}: {exc.reason}")
            raise
        except URLError as exc:
            self.logger.error(f"Network error contacting GitHub API ({url}): {exc.reason}")
            raise

    def authenticate(self) -> bool:
        """
        Verifies API connectivity and optional token validity against /user or /rate_limit.
        Unauthenticated requests remain usable at lower rate limits for public resources.
        """
        try:
            if self.token:
                self._request_json(f"{self.API_BASE_URL}/user")
                self.logger.info("GitHub Connector authenticated with GITHUB_TOKEN.")
            else:
                self._request_json(f"{self.API_BASE_URL}/rate_limit")
                self.logger.info("GitHub Connector initialized in unauthenticated public mode.")
            return True
        except Exception as exc:
            self.logger.error(f"GitHub authentication check failed: {exc}")
            return False

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Searches public GitHub repositories matching the query and returns structured candidates.
        """
        encoded_query = quote(query)
        per_page = max(1, min(max_results, 30))
        url = f"{self.API_BASE_URL}/search/repositories?q={encoded_query}&per_page={per_page}"
        self.logger.info(f"Searching GitHub repositories for query: '{query}'")

        try:
            data = self._request_json(url)
        except Exception as exc:
            self.logger.error(f"GitHub search failed for '{query}': {exc}")
            return []

        items = data.get("items", [])[:max_results]
        results: List[Dict[str, Any]] = []

        for repo in items:
            license_info = repo.get("license") or {}
            results.append(
                {
                    "dataset_id": repo.get("full_name", ""),
                    "name": repo.get("name", ""),
                    "platform": "GitHub",
                    "source_url": repo.get("html_url", ""),
                    "description": repo.get("description") or "",
                    "default_branch": repo.get("default_branch", "main"),
                    "license": license_info.get("spdx_id") or license_info.get("name"),
                    "stars": repo.get("stargazers_count", 0),
                    "updated_at": repo.get("updated_at"),
                }
            )

        self.logger.info(f"GitHub search returned {len(results)} repository candidates.")
        return results

    def get_metadata(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches repository metadata and lists candidate data files (.csv, .json, .jsonl, .parquet, .tsv)
        from the repository tree. `dataset_id` should be formatted as 'owner/repo'.
        """
        if "/" not in dataset_id:
            self.logger.error(f"Invalid GitHub dataset_id '{dataset_id}'. Expected 'owner/repo'.")
            return None

        owner, repo = dataset_id.split("/", 1)
        repo_url = f"{self.API_BASE_URL}/repos/{owner}/{repo}"
        self.logger.info(f"Fetching GitHub metadata for '{dataset_id}'...")

        try:
            repo_data = self._request_json(repo_url)
        except Exception as exc:
            self.logger.error(f"Failed to fetch GitHub repository metadata for '{dataset_id}': {exc}")
            return None

        default_branch = repo_data.get("default_branch", "main")
        license_info = repo_data.get("license") or {}
        candidate_files: List[str] = []
        supported_extensions = (".csv", ".json", ".jsonl", ".parquet", ".tsv", ".zip")

        tree_url = f"{self.API_BASE_URL}/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
        try:
            tree_data = self._request_json(tree_url)
            for node in tree_data.get("tree", []):
                if node.get("type") == "blob":
                    path_str = node.get("path", "")
                    if path_str.lower().endswith(supported_extensions):
                        candidate_files.append(path_str)
        except Exception as exc:
            self.logger.warning(f"Could not inspect file tree for '{dataset_id}': {exc}")

        return {
            "dataset_id": dataset_id,
            "name": repo_data.get("name", repo),
            "platform": "GitHub",
            "source_url": repo_data.get("html_url", f"https://github.com/{dataset_id}"),
            "description": repo_data.get("description") or "",
            "default_branch": default_branch,
            "license": license_info.get("spdx_id") or license_info.get("name"),
            "private": repo_data.get("private", False),
            "candidate_files": candidate_files,
            "updated_at": repo_data.get("updated_at"),
        }

    def download(self, dataset_id: str, filename: Optional[str] = None) -> Optional[str]:
        """
        Downloads a specific file from a public GitHub repository using `dataset_id` ('owner/repo')
        and `filename` (path inside the repo). If `filename` is omitted, selects the first
        candidate data file discovered in the repository.
        """
        if "/" not in dataset_id:
            self.logger.error(f"Invalid GitHub dataset_id '{dataset_id}'. Expected 'owner/repo'.")
            return None

        metadata = self.get_metadata(dataset_id)
        if not metadata:
            return None

        if metadata.get("private"):
            self.logger.warning(f"Repository '{dataset_id}' is private; skipping download.")
            return None

        target_path_in_repo = filename
        if not target_path_in_repo:
            candidates = metadata.get("candidate_files") or []
            if not candidates:
                self.logger.warning(f"No candidate data files found in '{dataset_id}'.")
                return None
            target_path_in_repo = candidates[0]

        owner, repo = dataset_id.split("/", 1)
        branch = metadata.get("default_branch", "main")
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{target_path_in_repo.lstrip('/')}"

        safe_repo = dataset_id.replace("/", "_")
        target_dir = self.output_dir / safe_repo
        target_dir.mkdir(parents=True, exist_ok=True)
        local_filename = Path(target_path_in_repo).name
        output_file = target_dir / local_filename

        self.logger.info(f"Downloading '{target_path_in_repo}' from '{dataset_id}' to '{output_file}'...")
        request = Request(raw_url, headers=self._build_headers(accept="application/octet-stream"))

        try:
            with urlopen(request, timeout=60) as response, open(output_file, "wb") as out_f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    out_f.write(chunk)

            self.logger.info(f"Successfully downloaded GitHub file to: {output_file}")
            return str(output_file)
        except Exception as exc:
            self.logger.error(f"Failed to download '{raw_url}': {exc}")
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