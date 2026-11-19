# DataForge Backend: Handoff for Persons 3 to 6

Base URL: `http://localhost:5000/api/v1`. Interactive docs: `http://localhost:5000/docs`.
Login: open `/auth/google/login` in the browser (use `localhost`, not `127.0.0.1`). All other endpoints need the login cookie.
Other users' data always returns 404.

## Endpoints

| Area | Method and path | Purpose |
|---|---|---|
| Auth | GET `/auth/google/login` | Start Google login |
| Auth | GET `/auth/me` | Who is logged in |
| Auth | POST `/auth/logout` | Log out |
| Projects | POST `/projects`, GET `/projects` | Create, list (`status`, `limit`, `offset`) |
| Projects | GET, PATCH, DELETE `/projects/{id}` | View, rename or archive, delete (cascades) |
| Requests | POST `/requests` | Submit a dataset request |
| Requests | GET `/requests` | List (`project_id`, `status`, `limit`, `offset`) |
| Requests | GET `/requests/{id}`, `/requests/{id}/status` | View, status only |
| Requests | POST `/requests/{id}/cancel` | Cancel (pending or processing only) |
| Requests | POST `/requests/{id}/run` | Run the pipeline (pending only) |
| Requests | GET `/requests/{id}/stages` | Pipeline progress |
| Requests | GET `/requests/{id}/summary` | Request, stages, dataset, quality, lineage |
| Strategy | POST `/strategy/preview` | Dry run of the adaptive engine |
| Datasets | GET `/datasets`, GET `/datasets/{id}` | List (`project_id`, `request_id`), view |
| Datasets | GET `/datasets/{id}/quality` | Latest quality report |
| Datasets | GET `/datasets/{id}/lineage` | Provenance rows |
| Exports | POST, GET `/datasets/{id}/exports`, GET `/exports/{id}` | Export a validated dataset |
| Dashboard | GET `/dashboard/stats` | Counts for the logged-in user |
| Health | GET `/health` | Server check |

## Allowed values (`app/core/constants.py`)

domain: phishing, attack_logs, vulnerable_code, user_behavior.
strategy: real_only, real_plus_synthetic, synthetic_only.
request status: pending, processing, completed, failed, cancelled.
job status: pending, running, completed, failed, retrying, cancelled.
file format: csv, json, jsonl, parquet, xlsx.
license status: unverified, verified_open, restricted. New sources start as `unverified`.
Changing any list needs a new Alembic migration and agreement from all of us.

## Formats we must agree on

- `required_features`, `features`: list of strings, for example `["url", "domain"]`. Matching is case-insensitive.
- `required_labels`: list of strings, for example `["benign", "malicious"]`.
- `class_distribution` and `label_counts`: object of label to record count, for example `{"benign": 20000}`.
- Quality scores: float from 0 to 1 (**Person 5 must confirm**; the database does not enforce it).
- Generation plan given to Person 6 (`strategy/preview` returns it too): domain, target_record_count, real_records_to_use, records_to_generate, missing_features, missing_labels, class_minimums, required_labels. If `records_to_generate` is 0 and `missing_features` is not empty, add the columns to existing rows instead of generating new rows.
- Lineage: a `real` row has `original_source_id` and no `generation_method`. A `synthetic` row has `generation_method` and no source. The database rejects anything else.

## What is still mocked

| Where | Mock today | Owner |
|---|---|---|
| `app/adapters/mock_adapters.py` `discover_sources(db, domain)` | One fake verified source per domain | Persons 3 and 4 |
| `app/adapters/mock_adapters.py` `assess_real_data(request)` | Returns 60% of the records, one feature missing, skewed labels | Person 5 |
| `pipeline_service._execute`, stage "acquisition" | Writes a fake completed job | Person 4 |
| `pipeline_service._execute`, stage "generation" | Writes a fake completed job | Person 6 |
| `pipeline_service._execute`, stage "dataset_build" | Fake `mock://` storage and fixed quality scores | Persons 5 and 6 |
| `dataset_service.create_export` | Fake `mock://exports/...` location | Whoever owns storage |

Real sources must start as `unverified`. Only the license check can change that. The engine never uses a source that is not `verified_open`.

## Known limits

- `/run` is synchronous. Real jobs need a background worker.
- Cancelling during a run is not detected.
- Archived projects reject new requests (our rule, change it if the team disagrees).
- `record_count` is capped at 5,000,000 (`MAX_RECORDS` in `app/schemas/request.py`).
- Engine thresholds live in `app/adaptive_engine/decision_config.py`.