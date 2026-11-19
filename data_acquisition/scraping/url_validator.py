import logging
from typing import Iterable, List, Optional, Set
from urllib.parse import urljoin, urlparse, urlunparse

logger = logging.getLogger(__name__)


class URLValidator:
    """
    Validates, normalizes, and filters candidate URLs for permitted web scraping
    and dataset discovery.
    """

    ALLOWED_SCHEMES = {"http", "https"}

    def __init__(self, allowed_domains: Optional[Iterable[str]] = None):
        self.allowed_domains: Optional[Set[str]] = (
            {d.strip().lower().lstrip(".") for d in allowed_domains if d and d.strip()}
            if allowed_domains is not None
            else None
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    def normalize_url(self, url: str, base_url: Optional[str] = None) -> Optional[str]:
        if not url or not isinstance(url, str):
            return None

        raw = url.strip()
        if not raw or raw.startswith(("#", "mailto:", "javascript:", "data:", "tel:")):
            return None

        resolved = urljoin(base_url, raw) if base_url else raw
        parsed = urlparse(resolved)

        if parsed.scheme.lower() not in self.ALLOWED_SCHEMES or not parsed.netloc:
            return None

        scheme = parsed.scheme.lower()
        hostname = (parsed.hostname or "").lower()
        if not hostname:
            return None

        port = parsed.port
        netloc = f"{hostname}:{port}" if port else hostname
        path = parsed.path or "/"

        # Drop fragment identifiers for canonical URL deduplication
        return urlunparse((scheme, netloc, path, "", parsed.query, ""))

    def is_domain_allowed(self, url: str) -> bool:
        if self.allowed_domains is None:
            return True

        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if not host:
            return False

        return any(host == dom or host.endswith(f".{dom}") for dom in self.allowed_domains)

    def is_valid_url(self, url: str, base_url: Optional[str] = None) -> bool:
        normalized = self.normalize_url(url, base_url=base_url)
        if not normalized:
            return False
        return self.is_domain_allowed(normalized)

    def filter_urls(self, urls: Iterable[str], base_url: Optional[str] = None) -> List[str]:
        seen: Set[str] = set()
        valid: List[str] = []
        for u in urls:
            norm = self.normalize_url(u, base_url=base_url)
            if norm and self.is_domain_allowed(norm) and norm not in seen:
                seen.add(norm)
                valid.append(norm)
        return valid