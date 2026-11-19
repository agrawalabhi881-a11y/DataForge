import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from data_acquisition.scraping.url_validator import URLValidator

logger = logging.getLogger(__name__)


class HTMLParser:
    """
    Parses HTML documents to extract page titles, text content, navigation links,
    and candidate dataset download links.
    """

    DATA_EXTENSIONS = (
        ".csv",
        ".tsv",
        ".json",
        ".jsonl",
        ".parquet",
        ".xlsx",
        ".xls",
        ".zip",
        ".tar",
        ".gz",
        ".tgz",
        ".7z",
    )

    def __init__(self, validator: Optional[URLValidator] = None):
        self.validator = validator or URLValidator()
        self.logger = logging.getLogger(self.__class__.__name__)

    def parse(self, html: str, base_url: Optional[str] = None) -> Dict[str, Any]:
        soup = BeautifulSoup(html or "", "html.parser")

        title_tag = soup.find("title")
        title = title_tag.get_text(" ", strip=True) if title_tag else ""

        h1_tag = soup.find("h1")
        heading = h1_tag.get_text(" ", strip=True) if h1_tag else ""

        meta_desc_tag = soup.find("meta", attrs={"name": lambda v: v and v.lower() == "description"})
        meta_description = ""
        if meta_desc_tag and meta_desc_tag.get("content"):
            meta_description = str(meta_desc_tag.get("content")).strip()

        links: List[Dict[str, str]] = []
        download_links: List[str] = []
        seen_links = set()
        seen_downloads = set()

        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href") or "").strip()
            anchor_text = " ".join(anchor.get_text(" ", strip=True).split())
            resolved = self.validator.normalize_url(href, base_url=base_url)
            if not resolved or not self.validator.is_domain_allowed(resolved):
                continue

            if resolved not in seen_links:
                seen_links.add(resolved)
                links.append({"url": resolved, "text": anchor_text})

            clean_path = resolved.split("?")[0].lower()
            is_data_file = any(clean_path.endswith(ext) for ext in self.DATA_EXTENSIONS)
            is_download_hint = any(
                token in resolved.lower() or token in anchor_text.lower()
                for token in ("download", "dataset", "dump", "export")
            )
            if (is_data_file or is_download_hint) and resolved not in seen_downloads:
                seen_downloads.add(resolved)
                download_links.append(resolved)

        body_text = " ".join(soup.get_text(" ", strip=True).split())

        return {
            "title": title or heading,
            "heading": heading,
            "meta_description": meta_description,
            "links": links,
            "download_links": download_links,
            "text_excerpt": body_text[:1500],
        }

    def resolve_link(self, href: str, base_url: Optional[str] = None) -> Optional[str]:
        if not href:
            return None
        return self.validator.normalize_url(urljoin(base_url or "", href))