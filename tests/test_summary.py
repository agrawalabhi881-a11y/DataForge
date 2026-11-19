def test_summary_before_run(api, make_project, make_request):
    rid = make_request(make_project()["id"])["id"]
    body = api.get(f"/api/v1/requests/{rid}/summary").json()
    assert body["stages"] == []
    assert body["dataset"] is None
    assert body["quality_report"] is None
    assert body["lineage"] == []


def test_summary_after_run(api, finished):
    body = api.get(f"/api/v1/requests/{finished.request_id}/summary").json()
    assert len(body["stages"]) == 5
    assert body["dataset"] is not None
    assert body["quality_report"] is not None
    assert len(body["lineage"]) == 2


def test_summary_unknown_request(api):
    assert api.get("/api/v1/requests/9999/summary").status_code == 404


def test_dashboard_stats(api, login, users, finished):
    stats = api.get("/api/v1/dashboard/stats").json()
    assert stats["projects"]["active"] == 1
    assert stats["requests"]["completed"] == 1
    assert stats["strategies"]["real_plus_synthetic"] == 1
    assert stats["datasets"]["mixed"] == 1
    assert stats["total_dataset_records"] == 50000
    assert set(stats["requests"]) == {
        "pending", "processing", "completed", "failed", "cancelled",
    }

    login(users.bob)  # another user sees only their own numbers
    other = api.get("/api/v1/dashboard/stats").json()
    assert other["requests"]["completed"] == 0
    assert other["total_dataset_records"] == 0


def test_dashboard_requires_login(client):
    assert client.get("/api/v1/dashboard/stats").status_code == 401