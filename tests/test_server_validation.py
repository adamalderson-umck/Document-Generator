import pytest
from pydantic import ValidationError
import asyncio

import server
from server import GenerateFinalPayload


def setup_function():
    server.sessions.clear()
    server.last_session_id = None


def test_generate_final_payload_defaults_extra_fields_for_legacy_clients():
    payload = GenerateFinalPayload.model_validate({})

    assert payload.session_id is None
    assert payload.extra_fields == {}


def test_generate_final_payload_rejects_non_object_body():
    with pytest.raises(ValidationError):
        GenerateFinalPayload.model_validate(["not", "an", "object"])


def test_generate_final_payload_allows_extra_fields_for_legacy_clients():
    payload = GenerateFinalPayload.model_validate({"extra_fields": {}})

    assert payload.session_id is None
    assert payload.extra_fields == {}


def test_generate_final_payload_rejects_empty_session_id():
    with pytest.raises(ValidationError):
        GenerateFinalPayload.model_validate({"session_id": "", "extra_fields": {}})


def test_generate_final_payload_rejects_non_string_session_id():
    with pytest.raises(ValidationError):
        GenerateFinalPayload.model_validate({"session_id": ["abc123"], "extra_fields": {}})


def test_generate_final_payload_rejects_non_mapping_extra_fields():
    with pytest.raises(ValidationError):
        GenerateFinalPayload.model_validate({"session_id": "abc123", "extra_fields": "bad"})


def test_resolve_session_uses_last_session_for_legacy_client_requests():
    session = {"data": {"date": "May 10, 2026"}}
    server.sessions["abc123"] = session
    server.last_session_id = "abc123"

    assert server.resolve_session(None) == session


def test_resolve_session_does_not_replace_unknown_explicit_session_id():
    session = {"data": {"date": "May 10, 2026"}}
    server.sessions["abc123"] = session
    server.last_session_id = "abc123"

    assert server.resolve_session("missing") is None


def test_resolve_session_loads_explicit_session_after_memory_reset(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "session_store_dir", str(tmp_path))
    monkeypatch.setattr(server, "last_session_file", str(tmp_path / "last_session_id.txt"))
    session = {"data": {"date": "May 10, 2026"}, "filename": "source.docx"}

    server.save_session("abc123", session)
    server.sessions.clear()
    server.last_session_id = None

    assert server.resolve_session("abc123") == session


def test_resolve_session_loads_last_session_after_memory_reset(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "session_store_dir", str(tmp_path))
    monkeypatch.setattr(server, "last_session_file", str(tmp_path / "last_session_id.txt"))
    session = {"data": {"date": "May 10, 2026"}, "filename": "source.docx"}

    server.save_session("abc123", session)
    server.sessions.clear()
    server.last_session_id = None

    assert server.resolve_session(None) == session


def test_generate_final_recovers_session_after_memory_reset(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "session_store_dir", str(tmp_path))
    monkeypatch.setattr(server, "last_session_file", str(tmp_path / "last_session_id.txt"))
    monkeypatch.setattr(server, "merge_site_config", lambda data: dict(data))
    monkeypatch.setattr(server, "generate_word_docs", lambda data, _templates, _outputs: ["output.docx"])
    session = {"data": {"date": "May 10, 2026"}, "filename": "source.docx"}

    server.save_session("abc123", session)
    server.sessions.clear()
    server.last_session_id = None

    result = asyncio.run(
        server.generate_final(
            GenerateFinalPayload.model_validate({"extra_fields": {"hymn_1_num": "95"}})
        )
    )

    assert result["status"] == "success"
    assert result["generated_files"] == ["output.docx"]
    assert server.sessions["abc123"]["data"]["hymn_1_num"] == "UMH 95"
