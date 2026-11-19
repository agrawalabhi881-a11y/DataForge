import pytest


def test_create_request(api, make_project, make_request):
    pid = make_project()["id"]
    request = make_request(pid, required_features=["url", "url", "domain"])
    assert request["status"] == "pending"
    assert request["strategy"] is None
    assert request["required_features"] == ["url", "domain"]  # duplicate removed


@pytest.mark.parametrize(
    "overrides",
    [
        {"domain": "banking"},
        {"record_count": 0},
        {"record_count": 5_000_001},
        {"output_format": "pdf"},
    ],
)
def test_bad_input_is_422(make_project, post_request, overrides):
    pid = make_project()["id"]
    assert post_request(pid, **overrides).status_code == 422


def test_unknown_project_is_404(api, post_request):
    assert post_request(9999).status_code == 404


def test_archived_project_is_409(api, make_project, post_request):
    pid = make_project()["id"]
    api.patch(f"/api/v1/projects/{pid}", json={"status": "archived"})
    assert post_request(pid).status_code == 409


def test_cancel_twice(api, make_project, make_request):
    rid = make_request(make_project()["id"])["id"]
    first = api.post(f"/api/v1/requests/{rid}/cancel")
    assert first.status_code == 200 and first.json()["status"] == "cancelled"
    assert api.post(f"/api/v1/requests/{rid}/cancel").status_code == 409


def test_other_user_gets_404(api, login, users, make_project, make_request):
    rid = make_request(make_project()["id"])["id"]
    login(users.bob)
    assert api.get(f"/api/v1/requests/{rid}").status_code == 404
    assert api.post(f"/api/v1/requests/{rid}/cancel").status_code == 404
    assert api.get("/api/v1/requests").json() == []