from pydantic import BaseModel, ConfigDict, Field, model_validator

from llm_schema.specifications.dataset import DatasetSpecification
from llm_schema.specifications.partial import PartialDatasetRequirements


class SpecificationParseResult(BaseModel):
    """
    Result of converting a natural-language request
    into a structured dataset specification.
    """
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    specification: DatasetSpecification | None = None

    partial_requirements: PartialDatasetRequirements | None = None

    missing_fields: list[str] = Field(default_factory=list)

    clarification_questions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_result(self):
        if self.specification is not None:
            if self.missing_fields:
                raise ValueError(
                    "A complete specification cannot have missing fields"
                )

            if self.partial_requirements is not None:
                raise ValueError(
                    "A complete specification cannot have partial requirements"
                )

        elif self.partial_requirements is None or not self.missing_fields:
            raise ValueError(
                "An incomplete result must contain partial requirements "
                "and identify missing fields"
            )

        return self

    @property
    def is_complete(self) -> bool:
        return self.specification is not None
