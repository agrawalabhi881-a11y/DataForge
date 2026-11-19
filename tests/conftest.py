from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app import models as _models  # noqa: F401  (registers all tables)
from app.core.config import settings
from app.core.security import get_current_user
from app.database.base import Base
from app.database.session import get_db
from app.main import app as fastapi_app
from app.models.user import User

TEST_DB = "dataforge_test"
TEST_URL = settings.database_url.set(database=TEST_DB)

# Safety: these tests drop and recreate tables, so never point them at the real database.
assert TEST_URL.database.endswith("_test")

REQUEST_BODY = {
    "requirements": "50,000 phishing URLs with benign, suspicious and malicious labels",
    "domain": "phishing",
    "record_count": 50000,
    "required_features": ["url", "domain", "url_length"],
    "required_labels": ["benign", "suspicious", "malicious"],
    "output_format": "parquet",
}


def _create_test_database() -> None:
    admin = create_engine(
        settings.database_url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    with admin.connect() as conn:
        exists = conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": TEST_DB}
        )
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def engine():
    _create_test_database()
    eng = create_engine(TEST_URL)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def client(engine):
    """A test client that uses the test database. Not logged in."""
    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.clear()

    # Empty every table so the next test starts clean.
    with engine.begin() as conn:
        tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture()
def users(client, engine):
    with sessionmaker(bind=engine)() as session:
        alice = User(email="alice@test.dev", name="Alice")
        bob = User(email="bob@test.dev", name="Bob")
        session.add_all([alice, bob])
        session.commit()
        return SimpleNamespace(alice=alice.id, bob=bob.id)


@pytest.fixture()
def login(client):
    def _login(user_id: int) -> None:
        fastapi_app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id)
    return _login


@pytest.fixture()
def api(client, users, login):
    """The client, already logged in as Alice."""
    login(users.alice)
    return client


@pytest.fixture()
def make_project(api):
    def _make(name="Phishing project"):
        r = api.post("/api/v1/projects", json={"name": name})
        assert r.status_code == 201, r.text
        return r.json()
    return _make


@pytest.fixture()
def post_request(api):
    """Returns the raw response, so tests can check error codes."""
    def _post(project_id, **overrides):
        body = {**REQUEST_BODY, "project_id": project_id, **overrides}
        return api.post("/api/v1/requests", json=body)
    return _post


@pytest.fixture()
def make_request(post_request):
    def _make(project_id, **overrides):
        r = post_request(project_id, **overrides)
        assert r.status_code == 201, r.text
        return r.json()
    return _make


@pytest.fixture()
def finished(api, make_project, make_request):
    """A project with one request that has already run through the pipeline."""
    project = make_project()
    request = make_request(project["id"])
    run = api.post(f"/api/v1/requests/{request['id']}/run")
    assert run.status_code == 200 and run.json()["status"] == "completed", run.text
    return SimpleNamespace(project_id=project["id"], request_id=request["id"])