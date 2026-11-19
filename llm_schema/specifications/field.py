
from pydantic import BaseModel, ConfigDict, Field, field_validator


class FieldRequirement(BaseModel):
    """
    Represents one field requested in a dataset.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    name: str = Field(min_length=1)
    required: bool = True
    description: str | None = None

    @field_validator("required", mode="before")
    @classmethod
    def default_required_when_none(cls, value):
        if value is None:
            return True
        return value
