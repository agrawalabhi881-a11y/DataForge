import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SourceRegistry:
    """
    Centralized registry for discovered and acquired dataset sources in DataForge.
    Tracks source metadata, license/access info, acquisition status, and storage URIs.
    """

    def __init__(self, registry_path: Optional[str] = None):
        self.registry_path: Optional[Path] = Path(registry_path) if registry_path else None
        self._sources: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

        if self.registry_path and self.registry_path.exists():
            self._load()

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _load(self) -> None:
        if not self.registry_path or not self.registry_path.exists():
            return
        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._sources = data
            elif isinstance(data, list):
                self._sources = {
                    str(item["source_id"]): item
                    for item in data
                    if isinstance(item, dict) and item.get("source_id")
                }
        except Exception as exc:
            self.logger.error(f"Failed to load source registry from '{self.registry_path}': {exc}")

    def _save(self) -> None:
        if not self.registry_path:
            return
        try:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(self._sources, f, indent=2, default=str)
        except Exception as exc:
            self.logger.error(f"Failed to persist source registry to '{self.registry_path}': {exc}")

    def _generate_next_source_id(self) -> str:
        existing_nums = []
        for sid in self._sources:
            if isinstance(sid, str) and sid.startswith("SRC_"):
                suffix = sid.removeprefix("SRC_")
                if suffix.isdigit():
                    existing_nums.append(int(suffix))
        next_num = (max(existing_nums) + 1) if existing_nums else 1
        return f"SRC_{next_num:03d}"

    def find_duplicate(self, source_record: Dict[str, Any]) -> Optional[str]:
        """
        Returns an existing `source_id` if a matching dataset_id + platform or
        matching source_url already exists in the registry.
        """
        dataset_id = source_record.get("dataset_id")
        platform = source_record.get("platform")
        source_url = source_record.get("source_url")

        for sid, existing in self._sources.items():
            same_id_and_platform = (
                dataset_id
                and existing.get("dataset_id") == dataset_id
                and (not platform or not existing.get("platform") or existing.get("platform") == platform)
            )
            same_url = source_url and existing.get("source_url") == source_url
            if same_id_and_platform or same_url:
                return sid
        return None

    def register_source(self, source_data: Dict[str, Any], allow_duplicate: bool = False) -> str:
        """
        Registers a new dataset source or updates an existing match if duplicate
        detection triggers. Returns the `source_id`.
        """
        payload = dict(source_data)
        if not allow_duplicate:
            dup_id = self.find_duplicate(payload)
            if dup_id:
                self.logger.info(f"Duplicate source detected; updating existing record '{dup_id}'.")
                self.update_source(dup_id, payload)
                return dup_id

        source_id = str(payload.get("source_id") or self._generate_next_source_id())
        now = self._now_iso()

        record: Dict[str, Any] = {
            "source_id": source_id,
            "dataset_name": payload.get("dataset_name") or payload.get("name") or source_id,
            "domain": payload.get("domain"),
            "platform": payload.get("platform"),
            "source_url": payload.get("source_url"),
            "dataset_identifier": payload.get("dataset_identifier") or payload.get("dataset_id"),
            "record_count": payload.get("record_count"),
            "features": payload.get("features") if payload.get("features") is not None else [],
            "format": payload.get("format"),
            "license": payload.get("license"),
            "access_status": payload.get("access_status") or "unknown",
            "access_conditions": payload.get("access_conditions"),
            "download_status": payload.get("download_status") or "pending",
            "acquisition_method": payload.get("acquisition_method"),
            "storage_uri": payload.get("storage_uri"),
            "checksum": payload.get("checksum"),
            "error": payload.get("error"),
            "created_at": payload.get("created_at") or now,
            "updated_at": now,
        }

        self._sources[source_id] = record
        self._save()
        self.logger.info(f"Registered source '{source_id}' ({record['dataset_name']}).")
        return source_id

    def update_source(self, source_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates fields on an existing source entry and returns the updated record."""
        if source_id not in self._sources:
            self.logger.warning(f"Cannot update unknown source_id '{source_id}'.")
            return None

        record = self._sources[source_id]
        for key, value in updates.items():
            if key == "source_id":
                continue
            if value is not None or key in {"storage_uri", "error", "download_status", "license"}:
                record[key] = value

        if "name" in updates and "dataset_name" not in updates and updates["name"]:
            record["dataset_name"] = updates["name"]
        if "dataset_id" in updates and "dataset_identifier" not in updates and updates["dataset_id"]:
            record["dataset_identifier"] = updates["dataset_id"]

        record["updated_at"] = self._now_iso()
        self._save()
        return dict(record)

    def update_download_status(
        self,
        source_id: str,
        status: str,
        storage_uri: Optional[str] = None,
        checksum: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Convenience helper to transition acquisition/download state."""
        updates: Dict[str, Any] = {"download_status": status}
        if storage_uri is not None:
            updates["storage_uri"] = storage_uri
        if checksum is not None:
            updates["checksum"] = checksum
        if error is not None:
            updates["error"] = error
        elif status in {"completed", "downloading", "pending"}:
            updates["error"] = None
        return self.update_source(source_id, updates)

    def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a copy of a source record by `source_id`."""
        item = self._sources.get(source_id)
        return dict(item) if item else None

    def list_sources(
        self,
        domain: Optional[str] = None,
        download_status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lists registered sources, optionally filtered by `domain` or `download_status`."""
        results: List[Dict[str, Any]] = []
        for item in self._sources.values():
            if domain and (item.get("domain") or "").lower() != domain.lower():
                continue
            if download_status and (item.get("download_status") or "").lower() != download_status.lower():
                continue
            results.append(dict(item))
        return results

    def get_storage_uri(self, source_id: str) -> Optional[str]:
        """Returns the raw storage URI for a source if available."""
        item = self._sources.get(source_id)
        return item.get("storage_uri") if item else None