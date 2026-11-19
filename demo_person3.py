"""Run a one-shot terminal demonstration of Person 3's requirement pipeline.

From the repository root:
    python demo_person3.py

This wrapper reuses the existing LLM parser, Pydantic specifications,
canonical schema registry, and deterministic mapping engine. It does not
collect, clean, or generate dataset records.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Ensure imports work when this file is launched directly from another folder.
REPOSITORY_ROOT = Path(__file__).resolve().parent
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from llm_schema.config.loader import load_provider_settings
from llm_schema.llm.client import MultiProviderLLMClient
from llm_schema.llm.requirement_parser import LLMRequirementParser
from llm_schema.mapping import compatibility_report, deterministic_mapping
from llm_schema.mapping.mapper import ColumnProfile, DatasetProfile
from llm_schema.schemas import get_schema_for_domain


def _print_section(title: str) -> None:
    print("\n" + "=" * 68)
    print(title.center(68))
    print("=" * 68)


def _print_mapping(mapping: Any, report: Any) -> None:
    print("\nRequested field mapping")
    print("-" * 68)
    print(f"{'Requested field':<25} {'Canonical field':<25} Status")
    print("-" * 68)

    mapped_sources = {item.source: item for item in mapping.mappings}
    for source in sorted(
        [item.name for item in _CURRENT_SPECIFICATION.fields],
        key=str.casefold,
    ):
        item = mapped_sources.get(source)
        if item is None:
            print(f"{source:<25} {'—':<25} UNMAPPED")
        else:
            print(f"{source:<25} {item.target:<25} MAPPED ({item.method})")

    if mapping.ambiguous:
        print("\nAmbiguous fields:")
        for source, candidates in sorted(mapping.ambiguous.items()):
            print(f"  - {source}: {', '.join(candidates)}")

    if mapping.unmapped_columns:
        print("\nUnmapped fields: " + ", ".join(mapping.unmapped_columns))

    print("\nCanonical schema coverage")
    print(f"  Missing required canonical fields: {report.missing or 'None'}")
    print(f"  Incompatible fields: {len(report.incompatible)}")
    print(f"  Indeterminate type checks: {len(report.indeterminate)}")
    print(
        "  Note: requested fields have no source data types yet; "
        "type compatibility is indeterminate until a dataset is inspected."
    )


_CURRENT_SPECIFICATION: Any = None


def run_demo(user_request: str) -> int:
    global _CURRENT_SPECIFICATION

    settings = load_provider_settings()
    if not settings.available_providers:
        print(
            "\nNo LLM provider is configured. Configure a provider API key "
            "and model in the repository-root .env file, then try again."
        )
        print("Supported providers: Gemini, Groq, OpenRouter, xAI, OpenAI.")
        return 2

    parser = LLMRequirementParser(MultiProviderLLMClient(settings))

    _print_section("1. NATURAL-LANGUAGE REQUIREMENT")
    print(user_request)

    _print_section("2. REQUIREMENT PARSING AND VALIDATION")
    result = parser.parse(user_request)

    print(f"Parsing status: {'COMPLETE' if result.is_complete else 'INCOMPLETE'}")

    if not result.is_complete:
        print("\nMore information is required:")
        for question in result.clarification_questions:
            print(f"  - {question}")

        print("\nPartial requirements:")
        print(result.partial_requirements.model_dump_json(indent=2))
        return 1

    specification = result.specification
    _CURRENT_SPECIFICATION = specification
    print(f"Domain: {specification.domain.value}")
    print(f"Target records: {specification.target_records}")
    print("Requested fields:")
    for field in specification.fields:
        required_text = "required" if field.required else "optional"
        print(f"  - {field.name} ({required_text})")

    _print_section("3. CANONICAL SCHEMA MAPPING")
    # The user's request provides field names, not source data types. Mark
    # those types unknown rather than inventing types or sample values.
    profile = DatasetProfile(
        path="<natural-language-requirement>",
        format="requirement",
        columns=[
            ColumnProfile(name=field.name, data_type="unknown")
            for field in specification.fields
        ],
    )
    mapping = deterministic_mapping(profile, specification.domain)
    report = compatibility_report(profile, mapping)
    canonical_model = get_schema_for_domain(specification.domain)
    _print_mapping(mapping, report)

    _print_section("4. CANONICAL SCHEMA FIELDS")
    for name, model_field in canonical_model.model_fields.items():
        required_text = "required" if model_field.is_required() else "optional"
        print(f"  - {name}: {model_field.annotation} ({required_text})")

    _print_section("5. FINAL STRUCTURED OUTPUT")
    output = {
        "specification": specification.model_dump(mode="json"),
        "canonical_schema": canonical_model.__name__,
        "mapping": mapping.model_dump(mode="json"),
        "compatibility_report": report.model_dump(mode="json"),
        "type_check_note": (
            "Indeterminate until an actual source dataset is inspected; "
            "this run maps requested field names only."
        ),
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    _print_section("DATAFORGE | PERSON 3")
    print("LLM REQUIREMENT PARSING & SCHEMA MAPPING")
    print("\nEnter one dataset requirement in natural language.")
    try:
        user_request = input("\nRequirement> ").strip()
        if not user_request:
            print("Input cannot be empty.")
            return 1
        return run_demo(user_request)
    except KeyboardInterrupt:
        print("\nDemo cancelled.")
        return 130
    except (ValueError, RuntimeError) as error:
        print(f"\nDataForge could not process this requirement: {error}")
        return 1
    except Exception as error:
        # Keep provider/library diagnostics visible without exposing secrets.
        print(f"\nUnexpected error: {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
