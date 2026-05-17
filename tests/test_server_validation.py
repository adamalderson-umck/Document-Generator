import asyncio
import json

from fastapi import HTTPException
import pytest
from pydantic import ValidationError

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

    def fake_generate_word_docs(data, _templates, _outputs):
        output_path = tmp_path / "output.docx"
        output_path.write_text("generated", encoding="utf-8")
        return [str(output_path)]

    monkeypatch.setattr(server, "generate_word_docs", fake_generate_word_docs)
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
    assert result["generated_files"] == [str(tmp_path / "output.docx")]
    assert server.sessions["abc123"]["data"]["hymn_1_num"] == "UMH 95"


def test_verify_generated_files_rejects_empty_generation_result():
    with pytest.raises(HTTPException) as exc_info:
        server.verify_generated_files([])

    assert exc_info.value.status_code == 500
    assert "no files were created" in exc_info.value.detail


def test_generate_final_rejects_missing_reported_output_file(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "session_store_dir", str(tmp_path))
    monkeypatch.setattr(server, "last_session_file", str(tmp_path / "last_session_id.txt"))
    monkeypatch.setattr(server, "merge_site_config", lambda data: dict(data))
    monkeypatch.setattr(
        server,
        "generate_word_docs",
        lambda data, _templates, _outputs: [str(tmp_path / "missing.docx")],
    )
    server.save_session("abc123", {"data": {"date": "May 10, 2026"}, "filename": "source.docx"})

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(server.generate_final(GenerateFinalPayload.model_validate({})))

    assert exc_info.value.status_code == 500
    assert "not found" in exc_info.value.detail


def test_list_weekly_reviews_returns_review_filenames(tmp_path, monkeypatch):
    review_dir = tmp_path / "weekly_reviews"
    review_dir.mkdir()
    (review_dir / "2026-05-17-review.json").write_text("{}", encoding="utf-8")
    (review_dir / "notes.txt").write_text("ignore", encoding="utf-8")
    monkeypatch.setattr(server, "weekly_reviews_dir", str(review_dir))

    result = server.list_weekly_reviews()

    assert result == {
        "status": "success",
        "reviews": ["2026-05-17-review.json"],
        "latest": "2026-05-17-review.json",
    }


def test_get_latest_weekly_review_returns_404_when_none(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "weekly_reviews_dir", str(tmp_path))

    with pytest.raises(HTTPException) as exc_info:
        server.get_latest_weekly_review()

    assert exc_info.value.status_code == 404


def test_get_latest_weekly_review_loads_file(tmp_path, monkeypatch):
    review_dir = tmp_path / "weekly_reviews"
    review_dir.mkdir()
    review = {"date": "May 17, 2026", "_review": {"status": "needs_review"}}
    (review_dir / "2026-05-17-review.json").write_text(
        json.dumps(review),
        encoding="utf-8",
    )
    monkeypatch.setattr(server, "weekly_reviews_dir", str(review_dir))

    result = server.get_latest_weekly_review()

    assert result["filename"] == "2026-05-17-review.json"
    assert result["review"] == review


def test_save_weekly_review_persists_json(tmp_path, monkeypatch):
    from server import WeeklyReviewPayload

    monkeypatch.setattr(server, "weekly_reviews_dir", str(tmp_path))
    review = {"date": "May 24, 2026", "_review": {"status": "needs_review"}}

    result = server.save_weekly_review(
        "2026-05-24-review.json",
        WeeklyReviewPayload.model_validate({"review": review}),
    )

    assert result["status"] == "success"
    assert result["filename"] == "2026-05-24-review.json"
    saved = json.loads((tmp_path / "2026-05-24-review.json").read_text(encoding="utf-8"))
    assert saved["date"] == "May 24, 2026"
    assert saved["_review"]["status"] == "needs_review"
    assert saved["_review"]["attention_fields"] == []


def test_save_weekly_review_refreshes_attention_and_sanitizes_sources(tmp_path, monkeypatch):
    from server import WeeklyReviewPayload

    monkeypatch.setattr(server, "weekly_reviews_dir", str(tmp_path))
    review = {
        "date": "May 24, 2026",
        "hymn_1_title": "Holy Spirit, Truth Divine",
        "hymn_1_num": "95",
        "_review": {
            "status": "needs_review",
            "sources": [{"kind": "music", "subject": "Bulletin", "body": "secret"}],
            "attention_fields": [
                {
                    "field": "hymn_1_num",
                    "reason": "usually_present_blank",
                    "message": "Usually present field is blank: hymn_1_num",
                }
            ],
        },
    }

    server.save_weekly_review(
        "2026-05-24-review.json",
        WeeklyReviewPayload.model_validate({"review": review}),
    )

    saved = json.loads((tmp_path / "2026-05-24-review.json").read_text(encoding="utf-8"))
    assert saved["_review"]["sources"] == [{"kind": "music", "subject": "Bulletin"}]
    assert saved["_review"]["attention_fields"] == []


def test_generate_from_weekly_review_uses_review_data(tmp_path, monkeypatch):
    from server import WeeklyReviewPayload

    monkeypatch.setattr(server, "weekly_reviews_dir", str(tmp_path))
    monkeypatch.setattr(server, "merge_site_config", lambda data: dict(data))
    monkeypatch.setattr(server, "get_missing_variables", lambda data, template_dir: ["optional_field"])

    def fake_generate_word_docs(data, _templates, _outputs):
        assert data["date"] == "May 24, 2026"
        assert data["hymn_1_num"] == "UMH 95"
        assert "_review" not in data
        output_path = tmp_path / "generated.docx"
        output_path.write_text("generated", encoding="utf-8")
        return [str(output_path)]

    monkeypatch.setattr(server, "generate_word_docs", fake_generate_word_docs)
    review = {"date": "May 24, 2026", "hymn_1_num": "95", "_review": {"status": "needs_review"}}
    (tmp_path / "2026-05-24-review.json").write_text(json.dumps(review), encoding="utf-8")

    result = server.generate_from_weekly_review(
        "2026-05-24-review.json",
        WeeklyReviewPayload.model_validate({"review": review}),
    )

    assert result["status"] == "success"
    assert result["missing_fields"] == ["optional_field"]
    assert result["generated_files"] == [str(tmp_path / "generated.docx")]


def test_generate_from_weekly_review_returns_404_for_missing_review_file(tmp_path, monkeypatch):
    from server import WeeklyReviewPayload

    monkeypatch.setattr(server, "weekly_reviews_dir", str(tmp_path))

    with pytest.raises(HTTPException) as exc_info:
        server.generate_from_weekly_review(
            "2026-05-24-review.json",
            WeeklyReviewPayload.model_validate({}),
        )

    assert exc_info.value.status_code == 404
