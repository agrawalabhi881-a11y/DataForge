
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from llm_schema.llm.requirement_parser import LLMRequirementParser


@pytest.fixture
def mock_client():
    return Mock()


@pytest.fixture
def parser(mock_client):
    return LLMRequirementParser(mock_client)


def test_parse_complete_requirements(parser, mock_client):
    response_data = {
        "domain": "phishing_urls",
        "target_records": 1000,
        "fields": [
            {"name": "url", "required": True},
            {"name": "label", "required": True},
        ],
    }

    mock_client.complete_with_fallback.return_value = SimpleNamespace(
        content=json.dumps(response_data)
    )

    result = parser.parse("I need 1000 phishing URL records")

    assert result.is_complete
    assert result.specification.target_records == 1000
    assert result.specification.domain == "phishing_urls"


def test_parse_incomplete_requirements(parser, mock_client):
    response_data = {
        "domain": "phishing_urls",
        "fields": [{"name": "url", "required": True}],
    }

    mock_client.complete_with_fallback.return_value = SimpleNamespace(
        content=json.dumps(response_data)
    )

    result = parser.parse("I need phishing URL records")

    assert not result.is_complete
    assert "target_records" in result.missing_fields


def test_parse_invalid_json(parser, mock_client):
    mock_client.complete_with_fallback.return_value = SimpleNamespace(
        content="This is not JSON"
    )

    with pytest.raises(ValueError, match="invalid JSON"):
        parser.parse("I need phishing URL records")


def test_parse_empty_input(parser):
    with pytest.raises(ValueError, match="cannot be empty"):
        parser.parse("   ")


def test_parse_rejects_unsupported_domain(parser, mock_client):
    response_data = {
        "domain": "unknown_domain",
        "target_records": 100,
        "fields": [{"name": "url", "required": True}],
    }

    mock_client.complete_with_fallback.return_value = SimpleNamespace(
        content=json.dumps(response_data)
    )

    with pytest.raises(ValidationError):
        parser.parse("I need a dataset")


def test_parse_rejects_json_array(parser, mock_client):
    mock_client.complete_with_fallback.return_value = SimpleNamespace(
        content='["phishing_urls", 100]'
    )

    with pytest.raises(ValidationError):
        parser.parse("I need a dataset")


def test_parse_markdown_wrapped_json(parser, mock_client):
    response_data = {
        "domain": "phishing_urls",
        "target_records": 500,
        "fields": [{"name": "url", "required": True}],
    }

    wrapped_json = f"```json\n{json.dumps(response_data)}\n```"

    mock_client.complete_with_fallback.return_value = SimpleNamespace(
        content=wrapped_json
    )

    result = parser.parse("I need 500 phishing URL records")

    assert result.is_complete
    assert result.specification.target_records == 500


def test_parse_plain_json(parser, mock_client):
    response_data = {
        "domain": "attack_logs",
        "target_records": 200,
        "fields": [{"name": "source_ip", "required": True}],
    }

    mock_client.complete_with_fallback.return_value = SimpleNamespace(
        content=json.dumps(response_data)
    )

    result = parser.parse("I need 200 attack log records")

    assert result.is_complete
    assert result.specification.domain == "attack_logs"
