from pydantic import BaseModel

from llm_schema.schemas.attack_logs import AttackLogRecord
from llm_schema.schemas.common import DatasetDomain
from llm_schema.schemas.phishing import PhishingURLRecord
from llm_schema.schemas.user_behavior import UserBehaviorRecord
from llm_schema.schemas.vulnerable_code import VulnerableCodeRecord

SCHEMA_REGISTRY: dict[DatasetDomain, type[BaseModel]] = {
    DatasetDomain.PHISHING_URLS: PhishingURLRecord,
    DatasetDomain.ATTACK_LOGS: AttackLogRecord,
    DatasetDomain.VULNERABLE_CODE: VulnerableCodeRecord,
    DatasetDomain.USER_BEHAVIOR: UserBehaviorRecord,
}


def get_schema_for_domain(domain: DatasetDomain | str) -> type[BaseModel]:
    """Return the canonical record model for a supported dataset domain."""
    try:
        normalized = domain if isinstance(domain, DatasetDomain) else DatasetDomain(domain)
        return SCHEMA_REGISTRY[normalized]
    except (ValueError, KeyError) as error:
        supported = ", ".join(item.value for item in SCHEMA_REGISTRY)
        raise ValueError(f"Unsupported dataset domain {domain!r}; expected one of: {supported}") from error
