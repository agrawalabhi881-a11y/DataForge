# DataForge - LLM and Schema Mapping Module

## Purpose and responsibilities

This package supports Person 3's LLM integration and schema-mapping workflow:

- Parse natural-language dataset requirements and identify missing information.
- Call configured LLM providers with fallback and structured-response validation.
- Define and validate canonical schemas for four cybersecurity dataset domains.
- Inspect CSV, JSON, JSONL/NDJSON, and Parquet dataset schemas.
- Map source columns deterministically or ask an LLM about unresolved columns.
- Report mapping compatibility and apply explicit source-label mappings.

It does not acquire or clean datasets, generate synthetic records, or provide
frontend/backend integration.

## Requirements and setup

Python 3.11 or newer is required. Run commands from the DataForge repository
root. Create and activate a virtual environment, then install the package
requirements:

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -r llm_schema/requirements.txt

The checked-in environment template is at the repository root. Copy it to a
local `.env` file:

    Copy-Item .env.example .env

Set the API key and model variables for each provider you intend to use:
`GEMINI_API_KEY`/`GEMINI_MODEL`, `GROQ_API_KEY`/`GROQ_MODEL`,
`OPENROUTER_API_KEY`/`OPENROUTER_MODEL`, `XAI_API_KEY`/`XAI_MODEL`, and
`OPENAI_API_KEY`/`OPENAI_MODEL`. These are the five providers supported by the
configuration loader. `LLM_PROVIDER_ORDER` controls fallback priority; the
template lists all five, while the code default when that variable is unset is
Gemini, Groq, then OpenRouter. Providers without both an API key and model are
skipped. `LLM_TIMEOUT_SECONDS` sets the request timeout (default: 30 seconds).
Never commit or print `.env` contents.

## Requirement parsing and LLM providers

`LLMRequirementParser` extracts the supported domain, requested record count,
fields, data preference, synthetic-fallback preference, and output format into
Pydantic specifications. It returns clarification questions when domain,
record count, or requested fields are missing, and rejects invalid structured
responses.

`MultiProviderLLMClient` tries configured providers in priority order. It falls
back after temporary service errors or invalid structured responses.
Authentication and other unexpected errors are not treated as temporary
failures and can be raised to the caller. API keys are held as secret values.

## Canonical schemas

The supported domains and models are:

| Domain | Canonical model |
| --- | --- |
| `phishing_urls` | `PhishingURLRecord` |
| `attack_logs` | `AttackLogRecord` |
| `vulnerable_code` | `VulnerableCodeRecord` |
| `user_behavior` | `UserBehaviorRecord` |

Use `get_schema_for_domain(domain)` with a domain enum or its string value.
The registry covers every current domain and is read-only. Canonical labels
remain open-vocabulary strings; no fixed label taxonomy is inferred.

## Dataset inspection and row counts

Use `inspect_dataset(path, sample_size=100)` to inspect column names, inferred
types, nullability, and up to three short sample values per column. A positive
`sample_size` bounds row sampling for CSV, JSONL/NDJSON, JSON record arrays, and
Parquet. JSON record arrays are read incrementally; Parquet reads a bounded
batch and uses file metadata for its total row count when available.

JSON object orientations other than record arrays retain pandas' full-read
behavior and can materialize the complete file. CSV, JSONL/NDJSON, and JSON
record-array total counts are `None` because calculating them could require a
full scan. Inferred types and nullability describe inspected rows only, not
necessarily the complete dataset.

`sampled_row_count` is the number of inspected rows. `row_count` is retained for
backward compatibility and has that same sampled-row meaning; it is never the
dataset total. `total_row_count` is an exact count only when reliably available
from Parquet metadata, and may otherwise be `None`.

## Column mapping and compatibility

`deterministic_mapping(profile, domain)` prefers normalized exact canonical
field names, then domain-specific aliases. Conflicts and unresolved columns
are reported as ambiguous or unmapped rather than assigned arbitrarily.

`llm_assisted_mapping(profile, domain, client)` asks the configured client only
about unresolved columns and validates returned structured mappings. Actual
sample values are excluded from prompts by default. Pass the keyword-only
`include_samples=True` only when sharing those values with the selected
provider is acceptable. The implementation does not log sample values.

`compatibility_report(profile, mapping)` reports:

- `matched`: known compatible dtype families.
- `incompatible`: known dtype-family mismatches.
- `indeterminate`: source or canonical dtype families that cannot be classified.
- `missing`: required canonical fields without a valid mapping.
- `extra`: unmapped or ambiguous source columns.
- `invalid_mappings`: mappings with missing/non-unique source columns, unknown
  targets, or duplicate source/target assignments.

Compatibility is inferred from dtype names; it does not validate every source
value or guarantee that values can be converted to the canonical field.

## Explicit label mapping

Use `map_label(source_label, explicit_mapping)` to convert one source label.
Mapping is exact and case-sensitive, with no normalization or automatic
guessing. Source strings, integers, finite floats, and booleans are supported;
the original source value and its type are retained in `LabelMapping`.

Null, missing, blank, non-finite, or unsupported source labels are rejected.
Mapping definitions must be non-empty mappings with non-null, non-blank
supported source keys and non-empty string canonical labels. Numeric matching
is type-sensitive (`1`, `1.0`, and `True` are distinct). If no exact entry
exists, `map_label` raises `ValueError`; callers must handle that explicitly
rather than dropping the label. Canonical labels are open-vocabulary strings,
not checked against an inferred or fixed taxonomy.

## Examples and tests

Run the independent local schema-mapping example without credentials:

    python examples/schema_mapping_demo.py

Run the full test suite and check installed dependency consistency:

    python -m pytest -v
    python -m pip check
