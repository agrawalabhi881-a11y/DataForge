"""DataForge - Data Engineering: auditable dataset lineage records."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping


def _json_safe(value: Any) -> Any:
    """Convert JSON-compatible values; reject opaque objects rather than silently lose data."""
    return json.loads(json.dumps(value, allow_nan=False, sort_keys=True))


@dataclass
class LineageTracker:
    dataset_id: str
    source_references: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.dataset_id, str) or not self.dataset_id.strip():
            raise ValueError("dataset_id must be a non-empty string")

    def add_source(self, source_id: str, *, source_version: str | None = None,
                   raw_reference: str | None = None, source_type: str = "real") -> dict[str, Any]:
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("source_id must be a non-empty string")
        if source_type not in {"real", "synthetic"}:
            raise ValueError("source_type must be real or synthetic")
        source = {"source_id": source_id, "source_version": source_version,
                  "raw_reference": raw_reference, "source_type": source_type}
        if source not in self.source_references:
            self.source_references.append(source)
        return source.copy()

    def record(self, operation: str, *, configuration: Mapping[str, Any] | None = None,
               input_version: str | None = None, output_version: str | None = None,
               statistics: Mapping[str, Any] | None = None,
               warnings: list[str] | None = None) -> dict[str, Any]:
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError("operation must be a non-empty string")
        if configuration is not None and not isinstance(configuration, Mapping):
            raise TypeError("configuration must be a mapping")
        if statistics is not None and not isinstance(statistics, Mapping):
            raise TypeError("statistics must be a mapping")
        if warnings is not None and (not isinstance(warnings, list) or
                                     not all(isinstance(w, str) for w in warnings)):
            raise TypeError("warnings must be a list of strings")
        event = {
            "event_id": f"EVT_{len(self.events) + 1:06d}",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "input_version": input_version,
            "output_version": output_version,
            "configuration": _json_safe(dict(configuration or {})),
            "statistics": _json_safe(dict(statistics or {})),
            "warnings": list(warnings or []),
        }
        self.events.append(event)
        return _json_safe(event)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe({"dataset_id": self.dataset_id,
                           "sources": self.source_references,
                           "events": self.events})

    def fingerprint(self) -> str:
        """Fingerprint the recorded history, including timestamps (not the dataset bytes)."""
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return sha256(payload.encode("utf-8")).hexdigest()

    def save_json(self, path: str | Path, *, overwrite: bool = False) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = "w" if overwrite else "x"
        with target.open(mode, encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2, ensure_ascii=False)
        return target

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LineageTracker":
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        tracker = cls(dataset_id=payload["dataset_id"])
        sources = payload.get("sources", [])
        events = payload.get("events", [])
        if not isinstance(sources, list) or not isinstance(events, list):
            raise ValueError("sources and events must be lists")
        tracker.source_references = _json_safe(sources)
        tracker.events = _json_safe(events)
        return tracker

    @classmethod
    def load_json(cls, path: str | Path) -> "LineageTracker":
        with Path(path).open(encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))
