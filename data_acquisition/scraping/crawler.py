from collections import deque
import logging
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from data_acquisition.scraping.scraper import WebScraper
from data_acquisition.scraping.url_validator import URLValidator

logger = logging.getLogger(__name__)


class WebCrawler:
    """
    Bounded, deduplicating crawler that traverses permitted pages from seed URLs
    and collects structured dataset candidates via WebScraper.
    """

    def __init__(
        self,
        scraper: Optional[WebScraper] = None,
        validator: Optional[URLValidator] = None,
        max_pages: int = 20,
        max_depth: int = 2,
    ):
        self.validator = validator or URLValidator()
        self.scraper = scraper or WebScraper(validator=self.validator)
        self.max_pages = max(1, int(max_pages))
        self.max_depth = max(0, int(max_depth))
        self.visited: Set[str] = set()
        self.errors: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(self.__class__.__name__)

    def crawl(
        self,
        seed_urls: Iterable[str],
        domain: Optional[str] = None,
        platform: str = "WebCrawler",
    ) -> List[Dict[str, Any]]:
        queue: deque[Tuple[str, int]] = deque()
        for seed in seed_urls:
            norm = self.validator.normalize_url(seed)
            if norm and self.validator.is_domain_allowed(norm) and norm not in self.visited:
                queue.append((norm, 0))

        discovered: List[Dict[str, Any]] = []
        pages_crawled = 0

        while queue and pages_crawled < self.max_pages:
            current_url, depth = queue.popleft()
            if current_url in self.visited:
                continue

            self.visited.add(current_url)
            pages_crawled += 1
            self.logger.info(f"Crawling [{pages_crawled}/{self.max_pages}] depth={depth}: {current_url}")

            page_data = self.scraper.scrape_page(
                url=current_url,
                domain=domain,
                platform=platform,
            )
            if not page_data:
                continue

            discovered.append(
                {
                    k: v
                    for k, v in page_data.items()
                    if k != "links"
                }
            )

            if depth < self.max_depth:
                for link_entry in page_data.get("links") or []:
                    next_url = link_entry.get("url") if isinstance(link_entry, dict) else str(link_entry)
                    norm_next = self.validator.normalize_url(next_url, base_url=current_url)
                    if (
                        norm_next
                        and self.validator.is_domain_allowed(norm_next)
                        and norm_next not in self.visited
                    ):
                        queue.append((norm_next, depth + 1))

        self.errors = list(self.scraper.errors)
        return discovered