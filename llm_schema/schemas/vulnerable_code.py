from pydantic import Field

from llm_schema.schemas.common import CanonicalRecord


class VulnerableCodeRecord(CanonicalRecord):
    """
    Canonical schema for vulnerable and secure code samples.
    """

    code_id: str = Field(min_length=1)
    code_snippet: str = Field(min_length=1)

    programming_language: str | None = None
    vulnerability_type: str | None = None
    cwe_id: str | None = None

    vulnerable_lines: list[int] | None = None

    label: str | None = None
