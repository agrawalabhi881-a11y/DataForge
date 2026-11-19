from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from app.core.constants import DOMAINS, LICENSE_STATUSES, STRATEGIES

Domain = Literal[*DOMAINS]
LicenseStatus = Literal[*LICENSE_STATUSES]
Strategy = Literal[*STRATEGIES]
Score = Annotated[float, Field(ge=0, le=1)]


class Requirements(BaseModel):
    """What the user asked for (comes from the dataset request)."""
    domain: Domain
    record_count: int = Field(gt=0)
    required_features: list[str] = Field(default_factory=list)
    required_labels: list[str] = Field(default_factory=list)


class SourceEligibility(BaseModel):
    """One discovered source (comes from Person 4 + our data_sources table)."""
    source_id: int
    license_status: LicenseStatus
    access_ok: bool = True
    acquired: bool = False


class RealDataAssessment(BaseModel):
    """What Person 5 reports about the processed real data. Scores are 0 to 1."""
    available_record_count: int = Field(default=0, ge=0)
    available_features: list[str] = Field(default_factory=list)
    label_counts: dict[str, int] = Field(default_factory=dict)
    completeness: Score = 0.0
    validity: Score = 0.0
    consistency: Score = 0.0
    relevance: Score = 0.0

    @field_validator("label_counts")
    @classmethod
    def counts_not_negative(cls, counts):
        if any(count < 0 for count in counts.values()):
            raise ValueError("label counts cannot be negative")
        return counts


class StrategyEvaluationRequest(BaseModel):
    requirements: Requirements
    assessment: RealDataAssessment
    sources: list[SourceEligibility] = Field(default_factory=list)


class GenerationPlan(BaseModel):
    """What Person 6 has to generate."""
    domain: str
    target_record_count: int
    real_records_to_use: int
    records_to_generate: int
    missing_features: list[str]
    missing_labels: list[str]
    class_minimums: dict[str, int]
    required_labels: list[str]


class StrategyDecision(BaseModel):
    strategy: Strategy
    reasons: list[str]
    warnings: list[str]
    metrics: dict
    generation_plan: GenerationPlan | None = None