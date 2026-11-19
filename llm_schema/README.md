# DataForge - LLM and Schema Mapping Module

## Purpose
Handles natural-language dataset requirements, cybersecurity
domain identification, canonical schemas, dataset schema
inspection, and intelligent column mapping.

## Supported Domains
1. Phishing URLs and malicious domains
2. Multi-stage attack logs
3. Vulnerable and secure code
4. User behavior and anomaly sequences

## Technology Stack
- Python
- Google Gemini API
- Pydantic
- Pandas and NumPy
- PyArrow
- python-dotenv
- Pytest

## Setup

Run commands from the DataForge repository root.

Create a virtual environment:

    python -m venv .venv

Activate on Windows PowerShell:

    .\.venv\Scripts\Activate.ps1

Install dependencies:

    pip install -r llm_schema/requirements.txt

Create your local environment file:

    Copy-Item llm_schema/.env.example llm_schema/.env

Add your Gemini API key to llm_schema/.env.

## Responsibilities
- Parse natural-language dataset requirements.
- Identify the cybersecurity domain.
- Define and validate canonical schemas.
- Inspect incoming dataset schemas.
- Map source columns to canonical fields.
- Generate mapping and compatibility reports.

## Individual schema mapping workflow

The canonical schema registry is exposed as `get_schema_for_domain(domain)`.
Use `inspect_dataset(path)` for CSV, JSON/JSONL, or Parquet column names,
inferred types, nullability, and sample values. `deterministic_mapping(profile,
domain)` applies normalized field names and domain aliases; unresolved columns
are reported as extra or ambiguous. If an LLM client is configured,
`llm_assisted_mapping(profile, domain, client)` asks it only about unresolved
columns and validates the response as structured JSON against canonical fields.

`compatibility_report(profile, mapping)` summarizes matched, missing required,
extra, and type-incompatible fields. Label conversion is intentionally explicit:
`map_label(original, mapping)` returns both the untouched source label and its
canonical label and raises when no exact mapping was provided.

The independent local example runs without credentials:

    python examples/schema_mapping_demo.py

To run the automated checks from the repository root:

    python -m pytest -v

## Scope Boundaries
This module does not acquire datasets, clean records,
generate synthetic records, or decide the final data strategy.
These responsibilities belong to other DataForge modules.
