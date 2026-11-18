from pydantic import BaseModel, ConfigDict, Field, model_validator

from llm_schema.specifications.dataset import DatasetSpecification


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

    missing_fields: list[str] = Field(default_factory=list)

    clarification_questions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_result(self):
        if self.specification is not None and self.missing_fields:
            raise ValueError(
                "A complete specification cannot have missing fields"
            )

        if self.specification is None and not self.missing_fields:
            raise ValueError(
                "An incomplete specification must identify missing fields"
            )

        return self

    @property
    def is_complete(self) -> bool:
        return self.specification is not None