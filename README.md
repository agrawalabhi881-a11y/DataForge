# DataForge Backend

FastAPI + PostgreSQL + Alembic.

## Setup
```
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env      # then fill in the values
alembic upgrade head
uvicorn app.main:app --reload --port 5000
```
Docs: http://localhost:5000/docs. Log in at /api/v1/auth/google/login (use localhost).

## Tests
```
pytest -q
```
Tests use a separate database called `dataforge_test`.

See docs/HANDOFF.md for endpoints and the formats shared with other team members.