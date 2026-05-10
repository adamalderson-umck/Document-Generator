import pytest
from pydantic import ValidationError

from server import GenerateFinalPayload


def test_generate_final_payload_defaults_extra_fields():
    payload = GenerateFinalPayload.model_validate({"session_id": "abc123"})

    assert payload.session_id == "abc123"
    assert payload.extra_fields == {}


def test_generate_final_payload_rejects_non_object_body():
    with pytest.raises(ValidationError):
        GenerateFinalPayload.model_validate(["not", "an", "object"])


def test_generate_final_payload_requires_session_id():
    with pytest.raises(ValidationError):
        GenerateFinalPayload.model_validate({"extra_fields": {}})


def test_generate_final_payload_rejects_empty_session_id():
    with pytest.raises(ValidationError):
        GenerateFinalPayload.model_validate({"session_id": "", "extra_fields": {}})


def test_generate_final_payload_rejects_non_string_session_id():
    with pytest.raises(ValidationError):
        GenerateFinalPayload.model_validate({"session_id": ["abc123"], "extra_fields": {}})


def test_generate_final_payload_rejects_non_mapping_extra_fields():
    with pytest.raises(ValidationError):
        GenerateFinalPayload.model_validate({"session_id": "abc123", "extra_fields": "bad"})
