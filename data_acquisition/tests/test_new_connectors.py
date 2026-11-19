import io
import json
from unittest.mock import patch

from data_acquisition.connectors.github_connector import GitHubConnector
from data_acquisition.connectors.open_data_connector import OpenDataConnector
from data_acquisition.connectors.uci_connector import UCIConnector


class _FakeHTTPResponse:
    """Minimal context-manager response object for mocking urllib.request.urlopen."""

    def __init__(self, body: bytes):
        self._stream = io.BytesIO(body)

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stream.close()
        return False


def test_github_connector_search_metadata_and_download(tmp_path):
    connector = GitHubConnector(output_dir=str(tmp_path / "github"), token="test-token")

    search_payload = {
        "items": [
            {
                "full_name": "example-org/phishing-urls",
                "name": "phishing-urls",
                "html_url": "https://github.com/example-org/phishing-urls",
                "description": "Phishing URL dataset",
                "default_branch": "main",
                "license": {"spdx_id": "MIT"},
                "stargazers_count": 42,
                "updated_at": "2026-10-01T00:00:00Z",
            }
        ]
    }
    repo_payload = {
        "name": "phishing-urls",
        "html_url": "https://github.com/example-org/phishing-urls",
        "description": "Phishing URL dataset",
        "default_branch": "main",
        "license": {"spdx_id": "MIT"},
        "private": False,
        "updated_at": "2026-10-01T00:00:00Z",
    }
    tree_payload = {
        "tree": [
            {"type": "blob", "path": "README.md"},
            {"type": "blob", "path": "data/urls.csv"},
            {"type": "blob", "path": "scripts/parse.py"},
        ]
    }

    def fake_urlopen(req, timeout=30):
        url = req.full_url
        if "/search/repositories" in url:
            return _FakeHTTPResponse(json.dumps(search_payload).encode("utf-8"))
        if url.endswith("/repos/example-org/phishing-urls"):
            return _FakeHTTPResponse(json.dumps(repo_payload).encode("utf-8"))
        if "/git/trees/main" in url:
            return _FakeHTTPResponse(json.dumps(tree_payload).encode("utf-8"))
        if url.endswith("/example-org/phishing-urls/main/data/urls.csv"):
            return _FakeHTTPResponse(b"url,label\nhttp://bad.example,phishing\n")
        raise AssertionError(f"Unexpected URL in test: {url}")

    with patch("data_acquisition.connectors.github_connector.urlopen", side_effect=fake_urlopen):
        results = connector.search("phishing dataset", max_results=5)
        assert len(results) == 1
        assert results[0]["dataset_id"] == "example-org/phishing-urls"
        assert results[0]["license"] == "MIT"

        meta = connector.get_metadata("example-org/phishing-urls")
        assert meta is not None
        assert meta["candidate_files"] == ["data/urls.csv"]

        downloaded = connector.download("example-org/phishing-urls")
        assert downloaded is not None
        assert downloaded.endswith("urls.csv")
        with open(downloaded, "rb") as f:
            assert b"http://bad.example" in f.read()


def test_github_connector_rejects_invalid_and_skips_private(tmp_path):
    connector = GitHubConnector(output_dir=str(tmp_path / "github"))
    assert connector.get_metadata("invalid_no_slash") is None
    assert connector.download("invalid_no_slash") is None

    private_repo = {
        "name": "secret-repo",
        "default_branch": "main",
        "private": True,
    }
    with patch(
        "data_acquisition.connectors.github_connector.urlopen",
        return_value=_FakeHTTPResponse(json.dumps(private_repo).encode("utf-8")),
    ):
        assert connector.download("org/secret-repo", filename="data.csv") is None


def test_uci_connector_search_metadata_and_download(tmp_path):
    connector = UCIConnector(output_dir=str(tmp_path / "uci"))

    search_payload = {
        "data": [
            {
                "id": 967,
                "name": "PhiUSIIL Phishing URL Dataset",
                "abstract": "URL features for phishing detection",
                "num_instances": 235795,
                "num_features": 55,
                "license": "CC BY 4.0",
            }
        ]
    }
    meta_payload = {
        "data": {
            "id": 967,
            "name": "PhiUSIIL Phishing URL Dataset",
            "abstract": "URL features for phishing detection",
            "num_instances": 235795,
            "num_features": 55,
            "target_col": "label",
            "license": "CC BY 4.0",
            "data_url": "https://example.org/uci/phiusiil.csv",
        }
    }

    def fake_urlopen(req, timeout=30):
        url = req.full_url
        if "/api/datasets?search=" in url:
            return _FakeHTTPResponse(json.dumps(search_payload).encode("utf-8"))
        if "/api/dataset?id=967" in url:
            return _FakeHTTPResponse(json.dumps(meta_payload).encode("utf-8"))
        if url == "https://example.org/uci/phiusiil.csv":
            return _FakeHTTPResponse(b"url,label\nhttps://ok.example,0\n")
        raise AssertionError(f"Unexpected URL in test: {url}")

    with patch("data_acquisition.connectors.uci_connector.urlopen", side_effect=fake_urlopen):
        found = connector.search("phishing")
        assert len(found) == 1
        assert found[0]["dataset_id"] == "967"
        assert found[0]["num_instances"] == 235795

        meta = connector.get_metadata("967")
        assert meta is not None
        assert meta["target_col"] == "label"

        out_path = connector.download("967")
        assert out_path is not None
        assert out_path.endswith("phiusiil.csv")


def test_open_data_connector_search_metadata_and_download(tmp_path):
    connector = OpenDataConnector(
        base_url="https://portal.example.org/api/3/action",
        output_dir=str(tmp_path / "open_data"),
    )

    pkg = {
        "id": "pkg-123",
        "name": "network-intrusion-logs",
        "title": "Network Intrusion Logs",
        "notes": "Sample network security dataset",
        "license_title": "Creative Commons Attribution",
        "resources": [
            {"id": "r1", "name": "events.csv", "format": "CSV", "url": "https://portal.example.org/files/events.csv"}
        ],
    }

    def fake_urlopen(req, timeout=30):
        url = req.full_url
        if "package_search" in url:
            return _FakeHTTPResponse(json.dumps({"result": {"results": [pkg]}}).encode("utf-8"))
        if "package_show" in url:
            return _FakeHTTPResponse(json.dumps({"result": pkg}).encode("utf-8"))
        if url == "https://portal.example.org/files/events.csv":
            return _FakeHTTPResponse(b"event_id,protocol\n1,TCP\n")
        raise AssertionError(f"Unexpected URL in test: {url}")

    with patch("data_acquisition.connectors.open_data_connector.urlopen", side_effect=fake_urlopen):
        items = connector.search("intrusion")
        assert len(items) == 1
        assert items[0]["formats"] == ["csv"]

        meta = connector.get_metadata("pkg-123")
        assert meta is not None
        assert len(meta["resources"]) == 1

        saved = connector.download("pkg-123")
        assert saved is not None
        assert saved.endswith("events.csv")