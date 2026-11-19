import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MetadataParser:
    """
    Extracts and normalizes dataset metadata from parsed HTML output or raw text.
    Leaves unknown fields as None rather than guessing values.
    """

    KNOWN_FORMATS = ("csv", "tsv", "json", "jsonl", "parquet", "xlsx", "xls", "zip", "tar", "gz")

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def _infer_format(self, parsed: Dict[str, Any]) -> Optional[str]:
        for link in parsed.get("download_links") or []:
            clean = str(link).split("?")[0].lower()
            for fmt in self.KNOWN_FORMATS:
                if clean.endswith(f".{fmt}"):
                    return fmt

        text_blob = f"{parsed.get('title', '')} {parsed.get('meta_description', '')}".lower()
        for fmt in self.KNOWN_FORMATS:
            if re.search(rf"\b{re.escape(fmt)}\b", text_blob):
                return fmt
        return None

    def _extract_record_count_hint(self, text: str) -> Optional[int]:
        if not text:
            return None
        match = re.search(
            r"\b(\d{1,3}(?:,\d{3})+|\d+)\s+(?:[a-z]+\s+){0,3}(?:records?|rows?|entries|samples|instances|events?)\b",
            text.lower(),
        )
        if not match:
            return None
        try:
            return int(match.group(1).replace(",", ""))
        except ValueError:
            return None

    def extract_dataset_metadata(
        self,
        parsed_page: Dict[str, Any],
        source_url: str,
        domain: Optional[str] = None,
        platform: str = "WebScraper",
    ) -> Dict[str, Any]:
        title = (parsed_page.get("title") or "").strip()
        description = (
            parsed_page.get("meta_description")
            or parsed_page.get("text_excerpt")
            or ""
        ).strip()
        download_links: List[str] = list(parsed_page.get("download_links") or [])
        fmt = self._infer_format(parsed_page)
        record_count = self._extract_record_count_hint(
            f"{title} {description} {parsed_page.get('text_excerpt', '')}"
        )

        return {
            "dataset_name": title or source_url,
            "domain": domain,
            "platform": platform,
            "source_url": source_url,
            "description": description[:500],
            "record_count": record_count,
            "features": [],
            "format": fmt,
            "download_links": download_links,
            "license": None,
            "access_status": "unknown",
        }