"""Explicit schema mapping and source preservation."""
import pandas as pd
import pytest
from data_engineering.schema.schema_transformer import transform_schema
from data_engineering.schema.schema_validator import validate_schema
from data_engineering.schema.column_mapper import inspect_column_mapping


def test_schema_mapping_and_validation():
    raw = pd.DataFrame({"URL": ["a.com"], "Risk": ["10"]})
    review = inspect_column_mapping(raw, {"URL": "url", "Risk": "risk_score"}, canonical_columns=["url", "risk_score"])
    assert review.valid
    transformed = transform_schema(raw, {"URL": "url", "Risk": "risk_score"}, column_types={"risk_score": "integer"}, required_columns=["url", "risk_score"])
    assert transformed.dataframe["risk_score"].iloc[0] == 10
    assert validate_schema(transformed.dataframe, required_columns=["url", "risk_score"], column_types={"risk_score": "integer"}).valid
    assert raw.columns.tolist() == ["URL", "Risk"]


def test_schema_rejects_collision():
    raw = pd.DataFrame({"URL": ["a"], "Link": ["b"]})
    with pytest.raises(ValueError):
        transform_schema(raw, {"URL": "url", "Link": "url"})
