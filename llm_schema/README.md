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

## Scope Boundaries
This module does not acquire datasets, clean records,
generate synthetic records, or decide the final data strategy.
These responsibilities belong to other DataForge modules.
