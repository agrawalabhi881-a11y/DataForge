from pydantic import BaseModel, ConfigDict, Field


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
