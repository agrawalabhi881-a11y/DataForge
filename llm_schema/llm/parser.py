from abc import ABC, abstractmethod

from llm_schema.specifications.parse_result import SpecificationParseResult


class RequirementParser(ABC):
    """
    Interface for converting natural-language requests
    into structured dataset requirements.
    """

    @abstractmethod
    def parse(self, user_input: str) -> SpecificationParseResult:
        """
        Parse a user's dataset request.

        Args:
            user_input: Natural-language dataset requirements.

        Returns:
            Complete or incomplete specification parse result.
        """
        pass