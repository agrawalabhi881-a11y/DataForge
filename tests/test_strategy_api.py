from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.main import app

BODY = {
    "requirements": {"domain": "phishing", "record_count": 1000,
                     "required_features": ["url_length"], "required_labels": ["benign", "malicious"]},
    "assessment": {"available_record_count": 1000, "available_features": ["url_length"],
                   "label_counts": {"benign": 500, "malicious": 500},
                   "completeness": 0.9, "validity": 0.9, "consistency": 0.9, "relevance": 0.9},
    "sources": [{"source_id": 1, "license_status": "verified_open", "acquired": True}],
}


def test_requires_login():
    app.dependency_overrides.clear()
    assert TestClient(app).post("/api/v1/strategy/preview", json=BODY).status_code == 401


def test_preview_returns_decision():
    app.dependency_overrides[get_current_user] = lambda: object()
    try:
        r = TestClient(app).post("/api/v1/strategy/preview", json=BODY)
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.json()["strategy"] == "real_only"


def test_bad_input_is_422():
    app.dependency_overrides[get_current_user] = lambda: object()
    try:
        bad = {**BODY, "requirements": {**BODY["requirements"], "record_count": 0}}
        r = TestClient(app).post("/api/v1/strategy/preview", json=bad)
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 422