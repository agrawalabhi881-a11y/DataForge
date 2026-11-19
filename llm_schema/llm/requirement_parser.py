
import json
import re

from llm_schema.llm.client import MultiProviderLLMClient
from llm_schema.llm.parser import RequirementParser

from llm_schema.specifications.dataset import DatasetSpecification
from llm_schema.specifications.partial import PartialDatasetRequirements
from llm_schema.specifications.parse_result import SpecificationParseResult
from llm_schema.specifications.requirements import find_missing_requirements


class LLMRequirementParser(RequirementParser):
    """Parse natural-language dataset requirements using an LLM."""

    def __init__(self, client: MultiProviderLLMClient):
        self.client = client

    def _build_prompt(self, user_input: str) -> str:
        """Build instructions for extracting dataset requirements."""

        return f"""
You are a cybersecurity dataset requirement extraction assistant.

Extract dataset requirements from the user's request.

Supported domains:
1. phishing_urls
2. attack_logs
3. vulnerable_code
4. user_behavior

Extract these properties:
- domain
- target_records
- fields (each with name, required, and description)
- data_preference
- allow_synthetic_fallback
- output_format

Allowed data_preference values:
- real_only
- synthetic_only
- real_preferred
- synthetic_preferred
- both

Allowed output_format values:
- csv
- json
- parquet

Rules:
- Extract only information explicitly stated or clearly implied.
- Do not invent missing requirements.
- Use null for unknown values.
- If fields are mentioned, preserve their intended names.
- Return only valid JSON.
- Do not include Markdown code fences or explanations.

User request:
{user_input}
"""

    def _extract_json(self, content: str) -> dict:
        """Extract JSON, including JSON wrapped in Markdown fences."""

        content = content.strip()

        content = re.sub(
            r"^```(?:json)?\s*|\s*```$",
            "",
            content,
            flags=re.IGNORECASE,
        ).strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as error:
            raise ValueError("LLM returned invalid JSON") from error

    def _validate_response(self, content: str) -> None:
        """Validate an LLM response before accepting its provider."""

        extracted_data = self._extract_json(content)

        partial = PartialDatasetRequirements.model_validate(
            extracted_data
        )

        missing = find_missing_requirements(partial)

        if not missing:
            DatasetSpecification.model_validate(
                partial.model_dump(exclude_none=True)
            )

    def parse(self, user_input: str) -> SpecificationParseResult:
        """Parse natural-language requirements into a structured result."""

        if not user_input.strip():
            raise ValueError("User input cannot be empty")

        prompt = self._build_prompt(user_input)
        response = self.client.complete_with_fallback(
            prompt,
            response_validator=self._validate_response,
        )

        extracted_data = self._extract_json(response.content)

        partial = PartialDatasetRequirements.model_validate(extracted_data)
        missing = find_missing_requirements(partial)

        if missing:
            return SpecificationParseResult(
                partial_requirements=partial,
                missing_fields=missing,
                clarification_questions=[
                    f"Please specify the {field.replace('_', ' ')}."
                    for field in missing
                ],
            )

        specification = DatasetSpecification.model_validate(
            partial.model_dump(exclude_none=True)
        )

        return SpecificationParseResult(specification=specification)
