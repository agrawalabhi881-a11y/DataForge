import pytest
from pydantic import ValidationError

from llm_schema.schemas import (
    PhishingURLRecord,
    AttackLogRecord,
    VulnerableCodeRecord,
    UserBehaviorRecord,
)


def test_valid_phishing_record():
    record = PhishingURLRecord(
        record_id="P001",
        url="https://example.com",
        https=True,
    )
    assert record.record_id == "P001"


def test_invalid_phishing_url_length():
    with pytest.raises(ValidationError):
        PhishingURLRecord(
            record_id="P002",
            url="https://example.com",
            url_length=-5,
        )


def test_valid_attack_log():
    record = AttackLogRecord(
        event_id="EV001",
        destination_port=443,
        protocol="TCP",
    )
    assert record.destination_port == 443


def test_invalid_attack_log_port():
    with pytest.raises(ValidationError):
        AttackLogRecord(
            event_id="EV002",
            destination_port=70000,
        )


def test_valid_vulnerable_code():
    record = VulnerableCodeRecord(
        code_id="C001",
        code_snippet="SELECT query using user input",
        vulnerability_type="SQL Injection",
    )
    assert record.vulnerability_type == "SQL Injection"


def test_valid_user_behavior():
    record = UserBehaviorRecord(
        event_id="U001",
        anomaly_score=0.85,
    )
    assert record.anomaly_score == 0.85


def test_invalid_anomaly_score():
    with pytest.raises(ValidationError):
        UserBehaviorRecord(
            event_id="U002",
            anomaly_score=1.5,
        )
