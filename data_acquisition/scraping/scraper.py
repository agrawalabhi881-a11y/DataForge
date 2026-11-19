import logging
import time
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from data_acquisition.scraping.html_parser import HTMLParser
from data_acquisition.scraping.metadata_parser import MetadataParser
from data_acquisition.scraping.url_validator import URLValidator

logger = logging.getLogger(__name__)


class WebScraper:
    """
    Fetches and parses permitted web pages for dataset discovery and metadata extraction,
    recording HTTP/network errors cleanly and enforcing configurable request pacing.
    """

    def __init__(
        self,
        validator: Optional[URLValidator] = None,
        html_parser: Optional[HTMLParser] = None,
        metadata_parser: Optional[MetadataParser] = None,
        timeout: float = 20.0,
        request_delay: float = 0.5,
        user_agent: str = "DataForge-Scraper/1.0 (+research-discovery)",
    ):
        self.validator = validator or URLValidator()
        self.html_parser = html_parser or HTMLParser(validator=self.validator)
        self.metadata_parser = metadata_parser or MetadataParser()
        self.timeout = float(timeout)
        self.request_delay = max(0.0, float(request_delay))
        self.user_agent = user_agent
        self._last_request_ts: float = 0.0
        self.errors: list[Dict[str, Any]] = []
        self.logger = logging.getLogger(self.__class__.__name__)

    def _pace_request(self) -> None:
        if self.request_delay <= 0:
            return
        elapsed = time.monotonic() - self._last_request_ts
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)

    def fetch_html(self, url: str) -> Optional[str]:
        normalized = self.validator.normalize_url(url)
        if not normalized or not self.validator.is_domain_allowed(normalized):
            err = {"url": url, "error": "URL failed validation or domain allowlist check."}
            self.errors.append(err)
            self.logger.warning(err["error"])
            return None

        self._pace_request()
        self._last_request_ts = time.monotonic()

        req = Request(
            normalized,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )

        try:
            with urlopen(req, timeout=self.timeout) as resp:
                charset = resp.headers.get_content_charset() or "utf-8"
                raw_bytes = resp.read()
                return raw_bytes.decode(charset, errors="replace")
        except HTTPError as exc:
            err = {"url": normalized, "status_code": exc.code, "error": f"HTTP {exc.code}: {exc.reason}"}
            self.errors.append(err)
            self.logger.warning(f"Scraper HTTP error for '{normalized}': {exc.code} {exc.reason}")
            return None
        except URLError as exc:
            err = {"url": normalized, "error": f"URL error: {exc.reason}"}
            self.errors.append(err)
            self.logger.warning(f"Scraper network error for '{normalized}': {exc.reason}")
            return None
        except Exception as exc:
            err = {"url": normalized, "error": str(exc)}
            self.errors.append(err)
            self.logger.error(f"Unexpected scraper error for '{normalized}': {exc}")
            return None

    def scrape_page(
        self,
        url: str,
        domain: Optional[str] = None,
        platform: str = "WebScraper",
    ) -> Optional[Dict[str, Any]]:
        html = self.fetch_html(url)
        if html is None:
            return None

        normalized_url = self.validator.normalize_url(url) or url
        parsed = self.html_parser.parse(html, base_url=normalized_url)
        metadata = self.metadata_parser.extract_dataset_metadata(
            parsed_page=parsed,
            source_url=normalized_url,
            domain=domain,
            platform=platform,
        )
        metadata["links"] = parsed.get("links", [])
        return metadata