from data_acquisition.schemas.acquisition_schema import (
    AcquisitionJobStatus,
    AcquisitionRequest,
    ProvenanceRecord,
)
from data_acquisition.schemas.dataset_schema import (
    DatasetRecord,
    DatasetSearchRequest,
)


def test_dataset_search_request_validation_and_conversion():
    empty_req = DatasetSearchRequest()
    assert empty_req.validate()

    bad_records_req = DatasetSearchRequest(query="phishing", min_records=-5)
    assert bad_records_req.validate()

    raw_dict = {
        "query": "phishing urls",
        "domain": "phishing",
        "min_records": 10000,
        "format": "csv",
        "require_verified_license": True,
    }
    req = DatasetSearchRequest.from_dict(raw_dict)
    assert req.validate() == []
    assert req.formats == ["csv"]

    reqs = req.to_requirements_dict()
    assert reqs["domain"] == "phishing"
    assert reqs["min_records"] == 10000


def test_dataset_record_roundtrip_and_validation():
    invalid_rec = DatasetRecord(dataset_name="")
    assert invalid_rec.validate()

    src = {
        "name": "Network Attack Logs",
        "dataset_id": "net-logs-01",
        "domain": "attack_logs",
        "platform": "Kaggle",
        "num_instances": 50000,
        "license": "MIT",
    }
    rec = DatasetRecord.from_dict(src)
    assert rec.validate() == []
    assert rec.dataset_name == "Network Attack Logs"
    assert rec.record_count == 50000

    as_dict = rec.to_dict()
    assert as_dict["dataset_id"] == "net-logs-01"
    assert as_dict["record_count"] == 50000


def test_acquisition_schemas_validation_and_provenance():
    bad_acq = AcquisitionRequest(dataset_id="", expected_sha256="not-a-hex")
    errors = bad_acq.validate()
    assert len(errors) == 2

    good_sha = "a" * 64
    acq = AcquisitionRequest.from_dict(
        {
            "source_id": "SRC_001",
            "download_url": "https://example.org/data.csv",
            "domain": "phishing",
            "expected_sha256": good_sha,
            "extract_archives": True,
        }
    )
    assert acq.dataset_id == "SRC_001"
    assert acq.validate() == []

    job = AcquisitionJobStatus.from_dict(
        {
            "job_id": "job_1",
            "source_id": "SRC_001",
            "status": "completed",
            "storage_uri": "storage/raw/phishing/src_001/data.csv",
            "checksum": good_sha,
            "file_size_bytes": 128,
            "attempts": 1,
        }
    )
    assert job.validate() == []
    assert job.to_dict()["status"] == "completed"

    prov = ProvenanceRecord.from_dict(
        {
            "source_id": "SRC_001",
            "source_url": "https://example.org/data.csv",
            "platform": "OpenData",
            "domain": "phishing",
            "storage_uri": "storage/raw/phishing/src_001/data.csv",
            "checksum": good_sha,
            "license": "CC-BY-4.0",
            "extra": {"ingested_by": "dataforge"},
        }
    )
    prov_dict = prov.to_dict()
    assert prov_dict["sha256"] == good_sha
    assert prov_dict["extra"]["ingested_by"] == "dataforge"