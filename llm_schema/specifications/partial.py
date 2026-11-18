from pydantic import BaseModel, ConfigDict, Field

from llm_schema.schemas.common import DatasetDomain
from llm_schema.specifications.enums import DataPreference, DatasetFormat
from llm_schema.specifications.field import FieldRequirement


class PartialDatasetRequirements(BaseModel):
    """
    Stores extracted dataset requirements before validation
    into a complete DatasetSpecification.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    domain: DatasetDomain | None = None

    target_records: int | None = Field(default=None, gt=0)

    fields: list[FieldRequirement] | None = None

    data_preference: DataPreference | None = None

    allow_synthetic_fallback: bool | None = None

    output_format: DatasetFormat | None = None