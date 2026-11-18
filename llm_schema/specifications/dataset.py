from pydantic import BaseModel, ConfigDict, Field, model_validator

from llm_schema.schemas.common import DatasetDomain
from llm_schema.specifications.enums import DataPreference, DatasetFormat
from llm_schema.specifications.field import FieldRequirement


class DatasetSpecification(BaseModel):
    """
    Structured representation of a user's dataset requirements.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    domain: DatasetDomain

    target_records: int = Field(gt=0)

    fields: list[FieldRequirement] = Field(min_length=1)

    data_preference: DataPreference = DataPreference.REAL_PREFERRED

    allow_synthetic_fallback: bool = False

    output_format: DatasetFormat = DatasetFormat.CSV

    @model_validator(mode="after")
    def validate_unique_fields(self):
        field_names = [field.name.lower() for field in self.fields]

        if len(field_names) != len(set(field_names)):
            raise ValueError("Duplicate field names are not allowed")

        return self
