def test_pipeline_run(api, finished):
    rid = finished.request_id
    request = api.get(f"/api/v1/requests/{rid}").json()
    assert request["status"] == "completed"
    assert request["strategy"] == "real_plus_synthetic"  # the mock has 60% of the records

    stages = api.get(f"/api/v1/requests/{rid}/stages").json()
    assert [s["stage"] for s in stages] == [
        "source_discovery", "strategy_selection", "acquisition", "generation", "dataset_build",
    ]
    assert all(s["status"] == "completed" for s in stages)


def test_cannot_run_twice(api, finished):
    assert api.post(f"/api/v1/requests/{finished.request_id}/run").status_code == 409


def test_cannot_run_cancelled_request(api, make_project, make_request):
    rid = make_request(make_project()["id"])["id"]
    api.post(f"/api/v1/requests/{rid}/cancel")
    assert api.post(f"/api/v1/requests/{rid}/run").status_code == 409


def test_pipeline_creates_a_dataset(api, finished):
    datasets = api.get(f"/api/v1/datasets?request_id={finished.request_id}").json()
    assert len(datasets) == 1
    assert datasets[0]["dataset_code"].startswith("DF_")
    assert datasets[0]["source_type"] == "mixed"
    assert datasets[0]["quality_status"] == "validated"