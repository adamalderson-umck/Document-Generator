import json

import pytest

from weekly_review import (
    CANONICAL_REVIEW_FIELDS,
    REVIEW_META_KEY,
    USUAL_FIELDS,
    attention_items,
    generator_data_from_review,
    initialize_review,
    latest_review_path,
    list_review_paths,
    refresh_review_attention,
    review_filename_for_date,
    safe_review_filename,
)


def test_review_filename_for_date_uses_iso_service_date():
    assert review_filename_for_date("2026-05-24") == "2026-05-24-review.json"


def test_safe_review_filename_rejects_path_traversal():
    with pytest.raises(ValueError, match="Invalid review filename"):
        safe_review_filename("../2026-05-24-review.json")


def test_safe_review_filename_rejects_non_review_json():
    with pytest.raises(ValueError, match="Invalid review filename"):
        safe_review_filename("notes.txt")


def test_list_review_paths_sorts_by_filename(tmp_path):
    review_dir = tmp_path / "weekly_reviews"
    review_dir.mkdir()
    (review_dir / "2026-05-17-review.json").write_text("{}", encoding="utf-8")
    (review_dir / "2026-05-24-review.json").write_text("{}", encoding="utf-8")

    assert [path.name for path in list_review_paths(review_dir)] == [
        "2026-05-17-review.json",
        "2026-05-24-review.json",
    ]


def test_latest_review_path_uses_latest_filename(tmp_path):
    review_dir = tmp_path / "weekly_reviews"
    review_dir.mkdir()
    old_path = review_dir / "2026-05-17-review.json"
    new_path = review_dir / "2026-05-24-review.json"
    old_path.write_text("{}", encoding="utf-8")
    new_path.write_text("{}", encoding="utf-8")

    assert latest_review_path(review_dir) == new_path


def test_latest_review_path_returns_none_for_empty_dir(tmp_path):
    assert latest_review_path(tmp_path) is None


def test_generator_data_from_review_strips_review_metadata():
    review = {
        "date": "May 24, 2026",
        "hymn_1_num": "95",
        REVIEW_META_KEY: {"status": "needs_review"},
    }

    assert generator_data_from_review(review) == {
        "date": "May 24, 2026",
        "hymn_1_num": "UMH 95",
    }


def test_canonical_review_fields_include_all_previous_extraction_channels():
    assert "service_time" in CANONICAL_REVIEW_FIELDS
    assert "special_title" in CANONICAL_REVIEW_FIELDS
    assert "communion_hymn_num" in CANONICAL_REVIEW_FIELDS
    assert "prelude_details" in CANONICAL_REVIEW_FIELDS
    assert "offertory_personnel" in CANONICAL_REVIEW_FIELDS
    assert "benediction_response_personnel" in CANONICAL_REVIEW_FIELDS


def test_initialize_review_includes_canonical_fields_template_fields_and_review_metadata():
    review = initialize_review(
        template_fields=["custom_template_field"],
        extracted_data={"date": "May 24, 2026", "custom_template_field": "Custom"},
        target_service_date="2026-05-24",
        sources=[{"kind": "source_doc", "subject": "May 24 worship notes"}],
    )

    assert review["date"] == "May 24, 2026"
    assert review["service_time"] == ""
    assert review["hymn_1_num"] == ""
    assert review["prelude_details"] == ""
    assert review["benediction_response_personnel"] == ""
    assert review["custom_template_field"] == "Custom"
    assert review[REVIEW_META_KEY]["target_service_date"] == "2026-05-24"
    assert review[REVIEW_META_KEY]["sources"] == [
        {"kind": "source_doc", "subject": "May 24 worship notes"}
    ]


def test_initialize_review_sanitizes_source_email_bodies():
    review = initialize_review(
        template_fields=["date"],
        extracted_data={"date": "May 24, 2026"},
        target_service_date="2026-05-24",
        sources=[
            {
                "kind": "music",
                "subject": "Bulletin",
                "body": "full email body",
                "attachments": [{"filename": "notes.docx", "body": "nested body"}],
            }
        ],
    )

    assert review[REVIEW_META_KEY]["sources"] == [
        {
            "kind": "music",
            "subject": "Bulletin",
            "attachments": [{"filename": "notes.docx"}],
        }
    ]


def test_attention_items_include_usual_blank_fields():
    review = initialize_review(
        template_fields=["date", "hymn_1_num", "prelude_title"],
        extracted_data={"date": "May 24, 2026"},
        target_service_date="2026-05-24",
    )

    items = attention_items(review, usual_fields={"hymn_1_num"})

    assert items == [
        {
            "field": "hymn_1_num",
            "reason": "usually_present_blank",
            "message": "Usually present field is blank: hymn_1_num",
        }
    ]


def test_refresh_review_attention_removes_resolved_blank_and_flags_structural_oddity():
    review = {
        "date": "May 24, 2026",
        "hymn_1_title": "Holy Spirit, Truth Divine",
        "hymn_1_num": "",
        "prelude_title": "Example",
        REVIEW_META_KEY: {
            "status": "needs_review",
            "attention_fields": [
                {
                    "field": "prelude_title",
                    "reason": "usually_present_blank",
                    "message": "Usually present field is blank: prelude_title",
                }
            ],
        },
    }

    refreshed = refresh_review_attention(review)

    assert {
        "field": "prelude_title",
        "reason": "usually_present_blank",
        "message": "Usually present field is blank: prelude_title",
    } not in refreshed[REVIEW_META_KEY]["attention_fields"]
    assert {
        "field": "hymn_1_num",
        "reason": "structurally_odd",
        "message": "Hymn title is present without a hymn number: hymn_1_num",
    } in refreshed[REVIEW_META_KEY]["attention_fields"]


def test_refresh_review_attention_flags_missing_sources():
    review = {"date": "", REVIEW_META_KEY: {"status": "source_missing"}}

    refreshed = refresh_review_attention(review)

    assert {
        "field": "",
        "reason": "source_selection_problem",
        "message": "Required source material is missing.",
    } in refreshed[REVIEW_META_KEY]["attention_fields"]


def test_attention_items_include_review_conflicts_and_low_confidence_fields():
    review = {
        "date": "May 24, 2026",
        REVIEW_META_KEY: {
            "low_confidence_fields": [
                {"field": "prelude_title", "message": "Multiple prelude candidates"}
            ],
            "conflicts": [
                {"field": "offertory_title", "message": "Two offertory emails disagree"}
            ],
        },
    }

    items = attention_items(review, usual_fields=set())

    assert items == [
        {
            "field": "prelude_title",
            "reason": "low_confidence",
            "message": "Multiple prelude candidates",
        },
        {
            "field": "offertory_title",
            "reason": "conflict",
            "message": "Two offertory emails disagree",
        },
    ]


def test_save_and_load_review_round_trip(tmp_path):
    from weekly_review import load_review, save_review

    path = tmp_path / "2026-05-24-review.json"
    review = {"date": "May 24, 2026", REVIEW_META_KEY: {"status": "needs_review"}}

    save_review(path, review)

    assert json.loads(path.read_text(encoding="utf-8")) == review
    assert load_review(path) == review


def test_save_review_strips_source_bodies(tmp_path):
    from weekly_review import load_review, save_review

    path = tmp_path / "2026-05-24-review.json"
    review = {
        "date": "May 24, 2026",
        REVIEW_META_KEY: {
            "status": "needs_review",
            "sources": [{"kind": "music", "subject": "Bulletin", "body": "secret"}],
        },
    }

    save_review(path, review)

    assert load_review(path)[REVIEW_META_KEY]["sources"] == [
        {"kind": "music", "subject": "Bulletin"}
    ]


def test_load_review_accepts_utf8_bom(tmp_path):
    from weekly_review import load_review

    path = tmp_path / "2026-05-24-review.json"
    path.write_text('{"date": "May 24, 2026"}', encoding="utf-8-sig")

    assert load_review(path) == {"date": "May 24, 2026"}
