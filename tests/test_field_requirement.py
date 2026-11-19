
from llm_schema.specifications.field import FieldRequirement


def test_required_defaults_to_true():
    field = FieldRequirement(name="url")
    assert field.required is True


def test_required_null_defaults_to_true():
    field = FieldRequirement(name="url", required=None)
    assert field.required is True


def test_explicit_false_is_preserved():
    field = FieldRequirement(name="optional_field", required=False)
    assert field.required is False
