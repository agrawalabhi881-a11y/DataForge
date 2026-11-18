from llm_schema.specifications.partial import PartialDatasetRequirements


def find_missing_requirements(
    requirements: PartialDatasetRequirements,
) -> list[str]:
    missing = []

    if requirements.domain is None:
        missing.append("domain")

    if requirements.target_records is None:
        missing.append("target_records")

    if not requirements.fields:
        missing.append("fields")

    return missing