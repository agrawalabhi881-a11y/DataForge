from pydantic import Field

from llm_schema.schemas.common import CanonicalRecord


class PhishingURLRecord(CanonicalRecord):
    """
    Canonical schema for phishing URLs and malicious domains.

    Features that are unavailable in the source dataset
    remain optional rather than being fabricated.
    """

    record_id: str = Field(min_length=1)
    url: str = Field(min_length=1)
    domain: str | None = None

    url_length: int | None = Field(default=None, ge=0)
    domain_length: int | None = Field(default=None, ge=0)
    subdomain_count: int | None = Field(default=None, ge=0)
    path_depth: int | None = Field(default=None, ge=0)

    https: bool | None = None
    has_ip_address: bool | None = None
    # Number of literal dot characters in the URL; distinct from subdomain_count.
    dot_count: int | None = Field(default=None, ge=0)
    entropy: float | None = Field(default=None, ge=0)

    # Preserve source labels instead of forcing a fixed vocabulary.
    label: str | None = None
