from sqlalchemy import text


def _dataset_id(api):
    return api.get("/api/v1/datasets").json()[0]["id"]


def test_quality_and_lineage(api, finished):
    did = _dataset_id(api)

    quality = api.get(f"/api/v1/datasets/{did}/quality")
    assert quality.status_code == 200
    assert quality.json()["completeness_score"] == 0.9

    lineage = api.get(f"/api/v1/datasets/{did}/lineage").json()
    assert {row["source_type"] for row in lineage} == {"real", "synthetic"}


def test_export(api, finished):
    did = _dataset_id(api)

    r = api.post(f"/api/v1/datasets/{did}/exports", json={"file_format": "csv"})
    assert r.status_code == 201
    assert r.json()["status"] == "completed"
    assert r.json()["export_location"].endswith(".csv")

    assert api.post(f"/api/v1/datasets/{did}/exports", json={"file_format": "pdf"}).status_code == 422
    assert len(api.get(f"/api/v1/datasets/{did}/exports").json()) == 1
    assert api.get(f"/api/v1/exports/{r.json()['id']}").status_code == 200


def test_unvalidated_dataset_cannot_be_exported(api, engine, finished):
    did = _dataset_id(api)
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE datasets SET quality_status = 'failed' WHERE id = :i"), {"i": did}
        )
    r = api.post(f"/api/v1/datasets/{did}/exports", json={"file_format": "csv"})
    assert r.status_code == 409


def test_other_user_gets_404(api, login, users, finished):
    did = _dataset_id(api)
    export_id = api.post(
        f"/api/v1/datasets/{did}/exports", json={"file_format": "csv"}
    ).json()["id"]

    login(users.bob)
    assert api.get(f"/api/v1/datasets/{did}").status_code == 404
    assert api.get(f"/api/v1/datasets/{did}/quality").status_code == 404
    assert api.get(f"/api/v1/exports/{export_id}").status_code == 404
    assert api.get("/api/v1/datasets").json() == []