# Weekly Review Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automation-first weekly review workflow where Codex prepares `inputs/weekly_reviews/YYYY-MM-DD-review.json` with all previously supported worship-order and music fields plus current template variables, the GUI opens that review, and the user edits attention fields before generating documents.

**Architecture:** Add a reusable Codex skill named `weekly-document-review` to hold the recurring workflow rules, with the cron automation reduced to a small scheduler prompt. Add a focused `weekly_review.py` module for review-file paths, validation, attention-field metadata, and generator-data conversion. Extend `server.py` with review JSON endpoints that reuse the existing `generate_word_docs()` path. Update the GUI to prefer the latest weekly review while preserving the current manual upload/paste workflow as a fallback.

**Tech Stack:** Python 3, FastAPI, Pydantic, `docxtpl`, `python-docx`, vanilla JavaScript, PowerShell Outlook COM for the local source-export helper, Codex cron automation.

---

## File Structure

- Create `C:\Users\kentu\.codex\skills\weekly-document-review\SKILL.md`: reusable Codex skill that owns the weekly review workflow.
- Create `C:\Users\kentu\.codex\skills\weekly-document-review\references\source-selection.md`: Outlook source-selection rules.
- Create `C:\Users\kentu\.codex\skills\weekly-document-review\references\review-json.md`: review JSON field coverage and `_review` rules.
- Create `weekly_review.py`: pure Python helpers for weekly review directories, safe filenames, latest review lookup, load/save, canonical worship/music review fields, attention-field normalization, stripping `_review`, applying hymn-number formatting, and review-field initialization.
- Create `tests/test_weekly_review.py`: unit tests for the helper module.
- Modify `server.py`: add weekly-review paths, Pydantic payloads, endpoints for list/latest/load/save/generate, and a reusable generation helper.
- Modify `tests/test_server_validation.py`: endpoint-level tests for review generation and persistence.
- Modify `templates/index.html`: add review-first GUI sections while keeping manual mode available.
- Modify `static/script.js`: load latest review on startup, render attention/all-field editors, save review edits, generate from review JSON, and preserve manual workflow behavior.
- Modify `static/style.css`: add restrained review-mode styles using existing visual vocabulary.
- Create `tools/export_weekly_sources.ps1`: optional deterministic Outlook source export helper for the Codex automation to call before extraction.
- Create `docs/automation/weekly-review-prompt.md`: thin stored prompt that invokes the `weekly-document-review` skill from the Codex cron automation.

## Task 0: Weekly Document Review Skill

**Files:**
- Create: `C:\Users\kentu\.codex\skills\weekly-document-review\SKILL.md`
- Create: `C:\Users\kentu\.codex\skills\weekly-document-review\references\source-selection.md`
- Create: `C:\Users\kentu\.codex\skills\weekly-document-review\references\review-json.md`
- Create: `C:\Users\kentu\.codex\skills\weekly-document-review\agents\openai.yaml`

- [ ] **Step 1: Initialize the skill directory**

Run:

```powershell
python C:\Users\kentu\.codex\skills\.system\skill-creator\scripts\init_skill.py weekly-document-review --path C:\Users\kentu\.codex\skills --resources references --interface display_name="Weekly Document Review" --interface short_description="Prepare weekly church document review JSON from Outlook and worship notes" --interface default_prompt="Prepare the weekly document review JSON for the upcoming Sunday."
```

Expected: creates `C:\Users\kentu\.codex\skills\weekly-document-review`.

- [ ] **Step 2: Write the skill body**

Replace `C:\Users\kentu\.codex\skills\weekly-document-review\SKILL.md` with:

```markdown
---
name: weekly-document-review
description: Prepare weekly church document review JSON packets for Document Generator. Use when Codex needs to extract worship-order and music fields from the local Outlook PST, worship-notes attachments, or weekly church planning emails, write `inputs/weekly_reviews/YYYY-MM-DD-review.json`, or run the Friday weekly document review automation.
---

# Weekly Document Review

## Workflow

1. Work in `E:\Coding Projects\Document-Generator` unless the user gives a different workspace.
2. Determine the target service date as the upcoming Sunday in `America/New_York`.
3. Read `CONTEXT.md` for current music terminology before extracting music fields.
4. Read `references/source-selection.md` for Outlook folders, subject matching, date windows, and attachment rules.
5. Export source material with `tools/export_weekly_sources.ps1` when available.
6. Discover current template variables from `docx_templates/`.
7. Build the review field set from canonical worship-order fields, canonical music fields, and current template variables.
8. Extract worship-order fields from the selected `10:30` worship-notes `.docx`.
9. Extract music fields from the week-before-service music emails.
10. Read `references/review-json.md` for the required output shape and attention-field rules.
11. Write `inputs/weekly_reviews/YYYY-MM-DD-review.json`.
12. Do not generate final documents unless the user explicitly asks.

## Guardrails

- Keep `CONTEXT.md` as the source of truth for music language; do not copy its detailed terminology into this skill.
- Use `*_details` only for secondary composer, arranger, harmonizer, editor, or additional-composer credit when `*_composer` has a primary credit.
- Leave normally absent fields blank.
- Record source metadata in `_review.sources`; do not include full email bodies in the final review JSON.
- If required sources are missing, still write a review JSON with blank fields and `_review.status` set to `source_missing`.
```

- [ ] **Step 3: Write source-selection reference**

Replace `C:\Users\kentu\.codex\skills\weekly-document-review\references\source-selection.md` with:

````markdown
# Source Selection

## Outlook Store

Use the local Outlook PST store named `Adam Alderson`.

## Source Worship Notes

- Folder: `Inbox\Staff\Nathan`
- Subject marker: `[Month] [D] worship notes`, for example `May 24 worship notes`
- Do not constrain worship-notes email search to the week before the service; these emails can arrive earlier.
- Select the `10:30` `.docx` attachment.
- If no matching Nathan email or `10:30` attachment exists, fall back to the newest plausible `.docx` in `inputs/` and record the fallback in `_review`.

## Music Emails

- Folder: `Inbox\Music`
- Date window: the week preceding the service date through the service date.
- Use the newest clarifying messages when later messages correct or complete earlier music information.

## Export Helper

When available, run:

```powershell
powershell -ExecutionPolicy Bypass -File tools\export_weekly_sources.ps1 -ServiceDate YYYY-MM-DD
```

Read the emitted `sources.json` and saved attachment paths.
````

- [ ] **Step 4: Write review JSON reference**

Replace `C:\Users\kentu\.codex\skills\weekly-document-review\references\review-json.md` with:

````markdown
# Review JSON

## Output Path

Write the review packet to:

```text
inputs/weekly_reviews/YYYY-MM-DD-review.json
```

Use the target service date in the filename.

## Field Coverage

Top-level keys are the union of:

- canonical worship-order fields from the source-document extraction channel
- canonical music fields from organist and choir extraction channels
- any additional variables used by the current templates
- `_review`

Canonical worship-order fields:

```text
date
service_time
sunday_title
special_title
is_communion_sunday
hymn_1_num
hymn_1_title
hymn_1_instr
hymn_2_num
hymn_2_title
hymn_2_instr
hymn_3_num
hymn_3_title
hymn_3_instr
communion_hymn_num
communion_hymn_title
doxology_num
reading_1_verse
reading_1_translation
reading_2_verse
reading_2_translation
```

Canonical music fields are each section with `title`, `composer`, `details`, and `personnel`:

```text
prelude
offertory
communion_piece
postlude
exit_music
introit
anthem
prayer_response
benediction_response
```

## Metadata

Include `_review` with:

```json
{
  "target_service_date": "YYYY-MM-DD",
  "status": "needs_review",
  "sources": [],
  "attention_fields": [],
  "missing_usual_fields": [],
  "low_confidence_fields": [],
  "conflicts": [],
  "notes": []
}
```

Use `_review.status = "source_missing"` when required source material is missing.

## Attention Fields

Add attention fields for:

- conflicting evidence
- low-confidence extraction
- source-selection problems
- structurally odd values, such as title without number
- usually-present blank fields

Blank normally-optional fields should not block generation.
````

- [ ] **Step 5: Validate the skill**

Run:

```powershell
python C:\Users\kentu\.codex\skills\.system\skill-creator\scripts\quick_validate.py C:\Users\kentu\.codex\skills\weekly-document-review
```

Expected: validation passes.

## Task 1: Weekly Review Core Module

**Files:**
- Create: `weekly_review.py`
- Create: `tests/test_weekly_review.py`

- [ ] **Step 1: Write failing tests for review path and filename safety**

Add `tests/test_weekly_review.py`:

```python
import json
from pathlib import Path

import pytest

from weekly_review import (
    REVIEW_META_KEY,
    generator_data_from_review,
    latest_review_path,
    list_review_paths,
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
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_weekly_review.py -v
```

Expected: fail with `ModuleNotFoundError: No module named 'weekly_review'`.

- [ ] **Step 3: Implement the review path helpers**

Create `weekly_review.py`:

```python
import json
import re
from pathlib import Path

from extractors import format_hymn_number


REVIEW_META_KEY = "_review"
REVIEW_FILENAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-review\.json$")


def review_filename_for_date(service_date):
    return f"{service_date}-review.json"


def safe_review_filename(filename):
    name = Path(filename).name
    if name != filename or not REVIEW_FILENAME_RE.match(name):
        raise ValueError(f"Invalid review filename: {filename}")
    return name


def list_review_paths(review_dir):
    path = Path(review_dir)
    if not path.exists():
        return []
    return sorted(
        candidate
        for candidate in path.glob("*-review.json")
        if REVIEW_FILENAME_RE.match(candidate.name)
    )


def latest_review_path(review_dir):
    paths = list_review_paths(review_dir)
    return paths[-1] if paths else None


def load_review(path):
    with Path(path).open(encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise ValueError("Weekly review must be a JSON object")
    return value


def save_review(path, review):
    if not isinstance(review, dict):
        raise ValueError("Weekly review must be a JSON object")
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(review, file, indent=2, ensure_ascii=False)
        file.write("\n")
    return output_path


def generator_data_from_review(review):
    data = {
        key: value
        for key, value in review.items()
        if key != REVIEW_META_KEY
    }
    for key, value in list(data.items()):
        if key.endswith("_num") or key in ("communion_hymn_num", "doxology_num"):
            if value:
                data[key] = format_hymn_number(value)
    return data
```

- [ ] **Step 4: Run the core tests and verify they pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_weekly_review.py -v
```

Expected: all tests in `tests/test_weekly_review.py` pass.

- [ ] **Step 5: Commit Task 1**

```powershell
git add weekly_review.py tests/test_weekly_review.py
git commit -m "Add weekly review file helpers"
```

## Task 2: Review Schema And Attention Helpers

**Files:**
- Modify: `weekly_review.py`
- Modify: `tests/test_weekly_review.py`

- [ ] **Step 1: Add failing tests for canonical review fields and attention fields**

Append to `tests/test_weekly_review.py`:

```python
from weekly_review import (
    CANONICAL_REVIEW_FIELDS,
    USUAL_FIELDS,
    attention_items,
    initialize_review,
)


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
```

- [ ] **Step 2: Run tests and verify the new tests fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_weekly_review.py -v
```

Expected: fail because `initialize_review`, `attention_items`, `CANONICAL_REVIEW_FIELDS`, and `USUAL_FIELDS` are not defined.

- [ ] **Step 3: Implement initialization and attention helpers**

Add to `weekly_review.py`:

```python
WORSHIP_ORDER_FIELDS = (
    "date",
    "service_time",
    "sunday_title",
    "special_title",
    "is_communion_sunday",
    "hymn_1_num",
    "hymn_1_title",
    "hymn_1_instr",
    "hymn_2_num",
    "hymn_2_title",
    "hymn_2_instr",
    "hymn_3_num",
    "hymn_3_title",
    "hymn_3_instr",
    "communion_hymn_num",
    "communion_hymn_title",
    "doxology_num",
    "reading_1_verse",
    "reading_1_translation",
    "reading_2_verse",
    "reading_2_translation",
)

MUSIC_SECTIONS = (
    "prelude",
    "offertory",
    "communion_piece",
    "postlude",
    "exit_music",
    "introit",
    "anthem",
    "prayer_response",
    "benediction_response",
)

MUSIC_FIELD_SUFFIXES = ("title", "composer", "details", "personnel")

MUSIC_FIELDS = tuple(
    f"{section}_{suffix}"
    for section in MUSIC_SECTIONS
    for suffix in MUSIC_FIELD_SUFFIXES
)

CANONICAL_REVIEW_FIELDS = WORSHIP_ORDER_FIELDS + MUSIC_FIELDS

USUAL_FIELDS = {
    "date",
    "service_time",
    "sunday_title",
    "hymn_1_num",
    "hymn_1_title",
    "hymn_2_num",
    "hymn_2_title",
    "hymn_3_num",
    "hymn_3_title",
    "doxology_num",
    "reading_1_verse",
    "reading_2_verse",
    "prelude_title",
    "postlude_title",
    "introit_title",
    "anthem_title",
}


def review_fields_for_template_fields(template_fields):
    canonical = list(CANONICAL_REVIEW_FIELDS)
    seen = set(canonical)
    for field in sorted(template_fields):
        if field not in seen:
            canonical.append(field)
            seen.add(field)
    return canonical


def initialize_review(
    template_fields,
    extracted_data,
    target_service_date,
    sources=None,
    notes=None,
):
    review = {}
    for field in review_fields_for_template_fields(template_fields):
        value = extracted_data.get(field, "")
        review[field] = value if value is not None else ""
    review[REVIEW_META_KEY] = {
        "target_service_date": target_service_date,
        "status": "needs_review",
        "sources": sources or [],
        "attention_fields": [],
        "missing_usual_fields": [],
        "low_confidence_fields": [],
        "conflicts": [],
        "notes": notes or [],
    }
    missing_usual = []
    for field in sorted(USUAL_FIELDS.intersection(review.keys())):
        if review.get(field, "") == "":
            missing_usual.append(
                {
                    "field": field,
                    "message": f"Usually present field is blank: {field}",
                }
            )
    review[REVIEW_META_KEY]["missing_usual_fields"] = missing_usual
    review[REVIEW_META_KEY]["attention_fields"] = attention_items(review)
    return review


def _normalized_review_item(item, reason):
    if isinstance(item, str):
        return {"field": item, "reason": reason, "message": item}
    field = item.get("field", "")
    return {
        "field": field,
        "reason": reason,
        "message": item.get("message") or item.get("reason") or field,
    }


def attention_items(review, usual_fields=None):
    meta = review.get(REVIEW_META_KEY, {})
    items = []
    for item in meta.get("low_confidence_fields", []):
        items.append(_normalized_review_item(item, "low_confidence"))
    for item in meta.get("conflicts", []):
        items.append(_normalized_review_item(item, "conflict"))
    for item in meta.get("missing_usual_fields", []):
        items.append(_normalized_review_item(item, "usually_present_blank"))

    if usual_fields is not None:
        for field in sorted(set(usual_fields)):
            if field in review and review.get(field, "") == "":
                candidate = {
                    "field": field,
                    "reason": "usually_present_blank",
                    "message": f"Usually present field is blank: {field}",
                }
                if candidate not in items:
                    items.append(candidate)
    return items
```

- [ ] **Step 4: Run review helper tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_weekly_review.py -v
```

Expected: all tests in `tests/test_weekly_review.py` pass.

- [ ] **Step 5: Commit Task 2**

```powershell
git add weekly_review.py tests/test_weekly_review.py
git commit -m "Add weekly review attention helpers"
```

## Task 3: Server Endpoints For Review Files

**Files:**
- Modify: `server.py`
- Modify: `tests/test_server_validation.py`

- [ ] **Step 1: Add failing tests for listing and loading latest review**

Append to `tests/test_server_validation.py`:

```python
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
    (review_dir / "2026-05-17-review.json").write_text(json.dumps(review), encoding="utf-8")
    monkeypatch.setattr(server, "weekly_reviews_dir", str(review_dir))

    result = server.get_latest_weekly_review()

    assert result["filename"] == "2026-05-17-review.json"
    assert result["review"] == review
```

Also add `import json` near the top of `tests/test_server_validation.py`.

- [ ] **Step 2: Run the new server tests and verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_server_validation.py -v
```

Expected: fail because the new review functions do not exist.

- [ ] **Step 3: Add review directories, imports, and list/load endpoints**

In `server.py`, update imports:

```python
from weekly_review import (
    latest_review_path,
    list_review_paths,
    load_review,
    safe_review_filename,
    save_review,
)
```

Add below `docx_templates_dir`:

```python
weekly_reviews_dir = os.path.join(inputs_dir, "weekly_reviews")
os.makedirs(weekly_reviews_dir, exist_ok=True)
```

Add below `/favicon.ico`:

```python
@app.get("/weekly_reviews")
def list_weekly_reviews():
    paths = list_review_paths(weekly_reviews_dir)
    filenames = [path.name for path in paths]
    return {
        "status": "success",
        "reviews": filenames,
        "latest": filenames[-1] if filenames else None,
    }


@app.get("/weekly_reviews/latest")
def get_latest_weekly_review():
    path = latest_review_path(weekly_reviews_dir)
    if not path:
        raise HTTPException(status_code=404, detail="No weekly review files found.")
    return {
        "status": "success",
        "filename": path.name,
        "review": load_review(path),
    }


@app.get("/weekly_reviews/{filename}")
def get_weekly_review(filename: str):
    try:
        safe_name = safe_review_filename(filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    path = os.path.join(weekly_reviews_dir, safe_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Weekly review file not found.")
    return {
        "status": "success",
        "filename": safe_name,
        "review": load_review(path),
    }
```

- [ ] **Step 4: Run server validation tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_server_validation.py -v
```

Expected: all tests in `tests/test_server_validation.py` pass.

- [ ] **Step 5: Commit Task 3**

```powershell
git add server.py tests/test_server_validation.py
git commit -m "Add weekly review list and load endpoints"
```

## Task 4: Save And Generate From Review JSON

**Files:**
- Modify: `server.py`
- Modify: `tests/test_server_validation.py`

- [ ] **Step 1: Add failing tests for saving and generating review files**

Append to `tests/test_server_validation.py`:

```python
from server import WeeklyReviewPayload


def test_save_weekly_review_persists_json(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "weekly_reviews_dir", str(tmp_path))
    review = {"date": "May 24, 2026", "_review": {"status": "needs_review"}}

    result = server.save_weekly_review(
        "2026-05-24-review.json",
        WeeklyReviewPayload.model_validate({"review": review}),
    )

    assert result["status"] == "success"
    assert result["filename"] == "2026-05-24-review.json"
    assert json.loads((tmp_path / "2026-05-24-review.json").read_text(encoding="utf-8")) == review


def test_generate_from_weekly_review_uses_review_data(tmp_path, monkeypatch):
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
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_server_validation.py -v
```

Expected: fail because `WeeklyReviewPayload`, `save_weekly_review`, and `generate_from_weekly_review` are not defined.

- [ ] **Step 3: Implement save and generate endpoints**

In `server.py`, update weekly-review imports:

```python
from weekly_review import (
    generator_data_from_review,
    latest_review_path,
    list_review_paths,
    load_review,
    safe_review_filename,
    save_review,
)
```

Add Pydantic model below `GenerateFinalPayload`:

```python
class WeeklyReviewPayload(BaseModel):
    review: dict = Field(default_factory=dict)
```

Add helper below `verify_generated_files`:

```python
def generate_documents_from_data(data):
    current_data = merge_site_config(dict(data))
    missing_fields = get_missing_variables(current_data, docx_templates_dir)
    generated_files = generate_word_docs(current_data, docx_templates_dir, outputs_dir)
    verify_generated_files(generated_files)
    return current_data, missing_fields, generated_files
```

Update existing `generate_final()` to use the helper:

```python
        current_data.update(extra_fields)
        session["data"] = current_data
        if payload.session_id or last_session_id:
            save_session(payload.session_id or last_session_id, session)

        current_data, missing_fields, generated_files = generate_documents_from_data(current_data)
        session["data"] = current_data
```

Keep the existing response shape, and add `"missing_fields": missing_fields`.

Add review endpoints below `get_weekly_review()`:

```python
@app.post("/weekly_reviews/{filename}")
def save_weekly_review(filename: str, payload: WeeklyReviewPayload):
    try:
        safe_name = safe_review_filename(filename)
        path = os.path.join(weekly_reviews_dir, safe_name)
        save_review(path, payload.review)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "success", "filename": safe_name}


@app.post("/weekly_reviews/{filename}/generate")
def generate_from_weekly_review(filename: str, payload: WeeklyReviewPayload):
    try:
        safe_name = safe_review_filename(filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    path = os.path.join(weekly_reviews_dir, safe_name)
    review = payload.review or load_review(path)
    save_review(path, review)
    data = generator_data_from_review(review)
    current_data, missing_fields, generated_files = generate_documents_from_data(data)
    return {
        "status": "success",
        "message": "Documents Generated Successfully!",
        "output_dir": outputs_dir,
        "generated_files": generated_files or [],
        "missing_fields": missing_fields,
        "warnings": current_data.get("_parse_warnings", []),
    }
```

- [ ] **Step 4: Run server tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_server_validation.py -v
```

Expected: all tests in `tests/test_server_validation.py` pass.

- [ ] **Step 5: Run the broader test suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Expected: all tests pass.

- [ ] **Step 6: Commit Task 4**

```powershell
git add server.py tests/test_server_validation.py
git commit -m "Generate documents from weekly review JSON"
```

## Task 5: GUI Review Mode

**Files:**
- Modify: `templates/index.html`
- Modify: `static/script.js`
- Modify: `static/style.css`

- [ ] **Step 1: Add weekly review markup to the page**

In `templates/index.html`, insert this section after `</header>` and before the existing Step 1 section:

```html
        <section class="card hidden" id="weeklyReviewSection">
            <div class="section-heading-row">
                <div>
                    <h2>Weekly Review</h2>
                    <p class="sub-text" id="weeklyReviewSummary">Loading latest review...</p>
                </div>
                <button id="manualModeBtn" class="secondary-btn" type="button">Manual Mode</button>
            </div>

            <div class="source-list" id="reviewSources"></div>

            <h3>Needs Attention</h3>
            <div class="input-grid" id="attentionInputs"></div>

            <details class="all-fields-panel">
                <summary>All fields</summary>
                <div class="input-grid" id="allReviewInputs"></div>
            </details>

            <button id="generateReviewBtn" class="primary-btn" type="button">
                Generate Final Documents
            </button>
        </section>
```

Wrap the existing upload and email sections in a manual container:

```html
        <div id="manualWorkflow">
            <!-- existing Step 1, Step 2, Step 3 sections stay here -->
        </div>
```

- [ ] **Step 2: Add review-mode JavaScript**

In `static/script.js`, add element references near the top:

```javascript
const weeklyReviewSection = document.getElementById('weeklyReviewSection');
const weeklyReviewSummary = document.getElementById('weeklyReviewSummary');
const reviewSources = document.getElementById('reviewSources');
const attentionInputs = document.getElementById('attentionInputs');
const allReviewInputs = document.getElementById('allReviewInputs');
const generateReviewBtn = document.getElementById('generateReviewBtn');
const manualModeBtn = document.getElementById('manualModeBtn');
const manualWorkflow = document.getElementById('manualWorkflow');

let currentReviewFilename = null;
let currentReview = null;
```

Add these functions before the drag-and-drop section:

```javascript
function reviewMeta() {
    return currentReview && currentReview._review ? currentReview._review : {};
}

function editableReviewKeys() {
    return Object.keys(currentReview || {})
        .filter(key => key !== '_review')
        .sort();
}

function attentionKeys() {
    const meta = reviewMeta();
    const items = meta.attention_fields || [];
    const keys = items.map(item => typeof item === 'string' ? item : item.field).filter(Boolean);
    return [...new Set(keys)];
}

function syncReviewFromInputs() {
    document.querySelectorAll('[data-review-key]').forEach(input => {
        currentReview[input.dataset.reviewKey] = input.value;
    });
}

function buildReviewInput(key, reason = '') {
    const group = document.createElement('div');
    group.className = 'input-group';

    const label = document.createElement('label');
    label.textContent = formatLabel(key);

    const input = document.createElement('input');
    input.type = 'text';
    input.dataset.reviewKey = key;
    input.value = currentReview[key] === undefined || currentReview[key] === null ? '' : String(currentReview[key]);

    group.appendChild(label);
    if (reason) {
        const hint = document.createElement('div');
        hint.className = 'field-hint';
        hint.textContent = reason;
        group.appendChild(hint);
    }
    group.appendChild(input);
    return group;
}

function renderReviewSources() {
    reviewSources.innerHTML = '';
    const sources = reviewMeta().sources || [];
    sources.forEach(source => {
        const line = document.createElement('div');
        line.className = 'source-line';
        line.textContent = [source.kind, source.subject, source.attachment, source.received]
            .filter(Boolean)
            .join(' · ');
        reviewSources.appendChild(line);
    });
}

function renderReviewInputs() {
    attentionInputs.innerHTML = '';
    allReviewInputs.innerHTML = '';

    const meta = reviewMeta();
    const attentionByKey = {};
    (meta.attention_fields || []).forEach(item => {
        if (typeof item === 'string') {
            attentionByKey[item] = item;
        } else if (item && item.field) {
            attentionByKey[item.field] = item.message || item.reason || '';
        }
    });

    const keys = editableReviewKeys();
    const attention = attentionKeys();
    if (attention.length === 0) {
        const line = document.createElement('div');
        line.className = 'empty-state';
        line.textContent = 'No flagged fields. You can still inspect all fields below.';
        attentionInputs.appendChild(line);
    } else {
        attention.forEach(key => attentionInputs.appendChild(buildReviewInput(key, attentionByKey[key])));
    }
    keys.forEach(key => allReviewInputs.appendChild(buildReviewInput(key)));
}

function renderWeeklyReview() {
    const meta = reviewMeta();
    weeklyReviewSummary.textContent = `${currentReviewFilename} · ${meta.status || 'needs_review'}`;
    renderReviewSources();
    renderReviewInputs();
    weeklyReviewSection.classList.remove('hidden');
    manualWorkflow.classList.add('hidden');
}

async function loadLatestWeeklyReview() {
    try {
        const res = await fetch('/weekly_reviews/latest');
        if (res.status === 404) {
            manualWorkflow.classList.remove('hidden');
            log('No weekly review found. Manual workflow is ready.');
            return;
        }
        const data = await res.json();
        if (!res.ok) throw new Error(getErrorMessage(data, 'Could not load weekly review'));
        currentReviewFilename = data.filename;
        currentReview = data.review;
        log(`Loaded weekly review: ${currentReviewFilename}`, 'success');
        renderWeeklyReview();
    } catch (err) {
        manualWorkflow.classList.remove('hidden');
        log(`Weekly review unavailable: ${err.message}`, 'warning');
    }
}
```

Add event handlers near the existing button handlers:

```javascript
manualModeBtn.addEventListener('click', () => {
    weeklyReviewSection.classList.add('hidden');
    manualWorkflow.classList.remove('hidden');
});

generateReviewBtn.addEventListener('click', async () => {
    if (!currentReviewFilename || !currentReview) return;
    syncReviewFromInputs();
    generateReviewBtn.disabled = true;
    generateReviewBtn.textContent = 'Generating...';
    log('Saving review and generating final documents...');
    try {
        const res = await fetch(`/weekly_reviews/${currentReviewFilename}/generate`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({review: currentReview})
        });
        const data = await res.json();
        renderWarnings(data.warnings);
        if (!res.ok) throw new Error(getErrorMessage(data, 'Generation failed'));
        log('Success! Documents created.', 'success');
        data.generated_files.forEach(path => log(`Created: ${path}`));
        if (data.missing_fields && data.missing_fields.length) {
            log(`Still blank or absent in template data: ${data.missing_fields.join(', ')}`, 'warning');
        }
        generateReviewBtn.textContent = 'Done';
    } catch (err) {
        log(`Error: ${err.message}`, 'error');
        generateReviewBtn.disabled = false;
        generateReviewBtn.textContent = 'Retry Generation';
    }
});

loadLatestWeeklyReview();
```

- [ ] **Step 3: Add review-mode CSS**

Append to `static/style.css`:

```css
.section-heading-row {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
}

.secondary-btn {
    padding: 0.65rem 0.9rem;
    color: #e2e8f0;
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    cursor: pointer;
    font-weight: 700;
}

.source-list {
    margin: 1rem 0 1.5rem;
    display: grid;
    gap: 0.5rem;
}

.source-line,
.field-hint,
.empty-state {
    color: #cbd5e1;
    font-size: 0.9rem;
}

.field-hint {
    color: #fde68a;
}

.all-fields-panel {
    margin: 1.5rem 0;
}

.all-fields-panel summary {
    cursor: pointer;
    color: #bfdbfe;
    font-weight: 800;
    margin-bottom: 1rem;
}

@media (max-width: 720px) {
    .input-grid {
        grid-template-columns: 1fr;
    }

    .section-heading-row {
        flex-direction: column;
    }
}
```

- [ ] **Step 4: Manual browser verification**

Run:

```powershell
.\.venv\Scripts\python.exe -m uvicorn server:app --reload --port 8000
```

Open `http://127.0.0.1:8000`.

Expected with no review files: manual workflow is visible and the status log says no weekly review was found.

Create a local review fixture:

```powershell
New-Item -ItemType Directory -Force inputs\weekly_reviews
@'
{
  "date": "May 24, 2026",
  "hymn_1_num": "",
  "hymn_1_title": "Holy Spirit, Truth Divine",
  "is_communion_sunday": false,
  "_review": {
    "target_service_date": "2026-05-24",
    "status": "needs_review",
    "sources": [
      {
        "kind": "source_doc",
        "subject": "May 24 worship notes",
        "attachment": "Day of Pentecost 1030am.docx"
      }
    ],
    "attention_fields": [
      {
        "field": "hymn_1_num",
        "reason": "usually_present_blank",
        "message": "Usually present field is blank: hymn_1_num"
      }
    ],
    "missing_usual_fields": [],
    "low_confidence_fields": [],
    "conflicts": [],
    "notes": []
  }
}
'@ | Set-Content -Encoding UTF8 inputs\weekly_reviews\2026-05-24-review.json
```

Refresh the browser.

Expected: weekly review section appears, `hymn_1_num` appears under Needs Attention, all fields are visible inside the expanded all-fields panel, and Manual Mode reveals the old upload/paste workflow.

- [ ] **Step 5: Commit Task 5**

```powershell
git add templates/index.html static/script.js static/style.css
git commit -m "Add weekly review GUI mode"
```

## Task 6: Outlook Source Export Helper

**Files:**
- Create: `tools/export_weekly_sources.ps1`
- Create directory: `tools/`

- [ ] **Step 1: Create the PowerShell helper**

Create `tools/export_weekly_sources.ps1`:

```powershell
param(
  [Parameter(Mandatory=$true)]
  [string]$ServiceDate,

  [string]$StoreName = "Adam Alderson",
  [string]$OutputRoot = "tmp/weekly_review_sources"
)

$ErrorActionPreference = "Stop"
$service = [datetime]::ParseExact($ServiceDate, "yyyy-MM-dd", $null)
$subjectMarker = $service.ToString("MMMM d", [Globalization.CultureInfo]::InvariantCulture) + " worship notes"
$outputDir = Join-Path $OutputRoot $service.ToString("yyyy-MM-dd")
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$outlook = New-Object -ComObject Outlook.Application
$ns = $outlook.Session
$store = $null
for ($i = 1; $i -le $ns.Stores.Count; $i++) {
  $candidate = $ns.Stores.Item($i)
  if ($candidate.DisplayName -eq $StoreName) {
    $store = $candidate
    break
  }
}
if (-not $store) {
  throw "Outlook store not found: $StoreName"
}

function Find-Folder($folder, [string[]]$parts, [int]$idx) {
  if ($idx -ge $parts.Count) { return $folder }
  for ($i = 1; $i -le $folder.Folders.Count; $i++) {
    $child = $folder.Folders.Item($i)
    if ($child.Name -eq $parts[$idx]) {
      return Find-Folder $child $parts ($idx + 1)
    }
  }
  return $null
}

function Message-Record($item, $folderPath) {
  [PSCustomObject]@{
    folder = $folderPath
    received = try { ([datetime]$item.ReceivedTime).ToString("s") } catch { "" }
    sender = try { [string]$item.SenderName } catch { "" }
    from = try { [string]$item.SenderEmailAddress } catch { "" }
    subject = try { [string]$item.Subject } catch { "" }
    body = try { [string]$item.Body } catch { "" }
    attachments = @()
  }
}

$root = $store.GetRootFolder()
$nathan = Find-Folder $root @("Inbox", "Staff", "Nathan") 0
$music = Find-Folder $root @("Inbox", "Music") 0
if (-not $nathan) { throw "Nathan folder not found" }
if (-not $music) { throw "Music folder not found" }

$sourceMessages = @()
$nathanItems = $nathan.Items
$nathanItems.Sort("[ReceivedTime]", $true)
for ($i = 1; $i -le $nathanItems.Count; $i++) {
  $item = $nathanItems.Item($i)
  $subject = try { [string]$item.Subject } catch { "" }
  if ($subject -notlike "*$subjectMarker*") { continue }
  $record = Message-Record $item "Inbox\Staff\Nathan"
  $attachments = @()
  for ($a = 1; $a -le $item.Attachments.Count; $a++) {
    $att = $item.Attachments.Item($a)
    $savedPath = ""
    if ($att.FileName -like "*1030*.docx" -or $att.FileName -like "*10*30*.docx") {
      $savedPath = Join-Path $outputDir $att.FileName
      $att.SaveAsFile($savedPath)
    }
    $attachments += [PSCustomObject]@{
      filename = $att.FileName
      size = $att.Size
      saved_path = $savedPath
    }
  }
  $record.attachments = $attachments
  $sourceMessages += $record
}

$musicMessages = @()
$start = $service.AddDays(-6).Date
$end = $service.AddDays(1).Date
$filter = "[ReceivedTime] >= '$($start.ToString("MM/dd/yyyy hh:mm tt"))' AND [ReceivedTime] < '$($end.ToString("MM/dd/yyyy hh:mm tt"))'"
$musicItems = $music.Items
$musicItems.Sort("[ReceivedTime]", $true)
$restricted = $musicItems.Restrict($filter)
for ($i = 1; $i -le $restricted.Count; $i++) {
  $item = $restricted.Item($i)
  $messageClass = try { [string]$item.MessageClass } catch { "" }
  if ($messageClass -notlike "IPM.Note*") { continue }
  $musicMessages += Message-Record $item "Inbox\Music"
}

$payload = [PSCustomObject]@{
  service_date = $service.ToString("yyyy-MM-dd")
  subject_marker = $subjectMarker
  output_dir = (Resolve-Path $outputDir).Path
  source_messages = $sourceMessages
  music_messages = $musicMessages
}

$jsonPath = Join-Path $outputDir "sources.json"
$payload | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $jsonPath
Write-Output $jsonPath
```

- [ ] **Step 2: Run a syntax parse check**

Run:

```powershell
$null = [scriptblock]::Create((Get-Content -Raw tools\export_weekly_sources.ps1)); "syntax ok"
```

Expected: prints `syntax ok`.

- [ ] **Step 3: Manually verify with the May 17 sample**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File tools\export_weekly_sources.ps1 -ServiceDate 2026-05-17
```

Expected: prints a `tmp\weekly_review_sources\2026-05-17\sources.json` path.

Inspect:

```powershell
Get-Content tmp\weekly_review_sources\2026-05-17\sources.json | Select-String -Pattern "May 17 worship notes","Ascension Sunday 1030am.docx","Music for Sunday","Bulletin"
```

Expected: output includes those strings.

- [ ] **Step 4: Commit Task 6**

```powershell
git add tools/export_weekly_sources.ps1
git commit -m "Add Outlook weekly source export helper"
```

## Task 7: Skill-Backed Automation Prompt And Codex Automation

**Files:**
- Create: `docs/automation/weekly-review-prompt.md`

- [ ] **Step 1: Write the stored automation prompt**

Create `docs/automation/weekly-review-prompt.md`:

```markdown
# Weekly Review Automation Prompt

Use the `weekly-document-review` skill to prepare the weekly review JSON for the upcoming Sunday service.

Workspace: `E:\Coding Projects\Document-Generator`
Timezone: `America/New_York`
Output: `inputs/weekly_reviews/YYYY-MM-DD-review.json`

Do not generate final documents. The GUI review step handles generation.
```

- [ ] **Step 2: Commit the prompt file**

```powershell
git add docs/automation/weekly-review-prompt.md
git commit -m "Document weekly review automation prompt"
```

- [ ] **Step 3: Create the Codex cron automation**

Use the Codex automation tool with:

- `kind`: `cron`
- `name`: `Weekly document review packet`
- `cwds`: `E:\Coding Projects\Document-Generator`
- `executionEnvironment`: `local`
- `rrule`: `FREQ=WEEKLY;BYDAY=FR;BYHOUR=8;BYMINUTE=0;BYSECOND=0`
- `prompt`: the contents of `docs/automation/weekly-review-prompt.md`; this prompt intentionally delegates detailed workflow rules to the `weekly-document-review` skill
- `status`: `ACTIVE`

Expected: the automation is saved and scheduled for Friday mornings at 8:00 AM Eastern on the local workspace.

## Task 8: End-To-End Verification

**Files:**
- No code changes expected unless verification exposes a defect.

- [ ] **Step 1: Validate the Codex skill**

Run:

```powershell
python C:\Users\kentu\.codex\skills\.system\skill-creator\scripts\quick_validate.py C:\Users\kentu\.codex\skills\weekly-document-review
```

Expected: validation passes.

- [ ] **Step 2: Run the full Python test suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Expected: all tests pass.

- [ ] **Step 3: Run the May 17 source export**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File tools\export_weekly_sources.ps1 -ServiceDate 2026-05-17
```

Expected: creates `tmp\weekly_review_sources\2026-05-17\sources.json` and saves `Ascension Sunday 1030am.docx`.

- [ ] **Step 4: Create a May 17 review JSON fixture**

Run this command to create a review JSON from the known May 17 source document plus the previously verified music extraction:

```powershell
@'
import json
from pathlib import Path

from extractors import parse_source_doc
from generators import _get_template_variables, list_templates
from weekly_review import initialize_review, save_review

base = Path(r"E:\Coding Projects\Document-Generator")
source_doc = base / "tmp" / "weekly_review_sources" / "2026-05-17" / "Ascension Sunday 1030am.docx"
if not source_doc.exists():
    source_doc = base / "tmp" / "outlook_attachments" / "2026-05-17" / "Ascension Sunday 1030am.docx"

music = {
    "prelude_title": "Largo",
    "prelude_composer": "Elizabeth Sterling",
    "prelude_details": "",
    "prelude_personnel": "",
    "offertory_title": "Prelude on Thaxted",
    "offertory_composer": "",
    "offertory_details": "arr. Michael Helman",
    "offertory_personnel": "Chancel Ringers",
    "communion_piece_title": "",
    "communion_piece_composer": "",
    "communion_piece_details": "",
    "communion_piece_personnel": "",
    "postlude_title": "Toccata",
    "postlude_composer": "Gerald Near",
    "postlude_details": "",
    "postlude_personnel": "",
    "exit_music_title": "Andante",
    "exit_music_composer": "Johann Albrechtsberger",
    "exit_music_details": "",
    "exit_music_personnel": "",
    "introit_title": "The Head that Once Was Crowned with Thorns",
    "introit_composer": "Attr. to Jeremiah Clarke",
    "introit_details": "harm. by W. H. Monk",
    "introit_personnel": "",
    "anthem_title": "Laudate Dominum",
    "anthem_composer": "Gordon Young",
    "anthem_details": "",
    "anthem_personnel": "",
    "prayer_response_title": "",
    "prayer_response_composer": "",
    "prayer_response_details": "",
    "prayer_response_personnel": "",
    "benediction_response_title": "Yea, Amen! Let All Adore Thee",
    "benediction_response_composer": "Trad. English melody",
    "benediction_response_details": "harm. from The English Hymnal, 1906",
    "benediction_response_personnel": "",
}

template_fields = set()
for template in list_templates(base / "docx_templates"):
    template_fields.update(_get_template_variables(template))

extracted = parse_source_doc(str(source_doc))
extracted.update(music)
review = initialize_review(
    template_fields=template_fields,
    extracted_data=extracted,
    target_service_date="2026-05-17",
    sources=[
        {
            "kind": "source_doc",
            "folder": "Inbox\\Staff\\Nathan",
            "subject": "May 17 worship notes",
            "attachment": "Ascension Sunday 1030am.docx",
        },
        {
            "kind": "music_email_set",
            "folder": "Inbox\\Music",
            "date_window": "2026-05-11 through 2026-05-17",
        },
    ],
)
save_review(base / "inputs" / "weekly_reviews" / "2026-05-17-review.json", review)
print(json.dumps({"path": "inputs/weekly_reviews/2026-05-17-review.json", "fields": len(review)}, indent=2))
'@ | .\.venv\Scripts\python.exe -
```

Expected: prints a JSON object with `"path": "inputs/weekly_reviews/2026-05-17-review.json"` and a positive field count.

- [ ] **Step 5: Start the local app**

Run:

```powershell
.\.venv\Scripts\python.exe -m uvicorn server:app --port 8000
```

Expected: server starts on `http://127.0.0.1:8000`.

- [ ] **Step 6: Verify review mode in the GUI**

Open `http://127.0.0.1:8000`.

Expected:

- latest weekly review loads automatically
- source summary is visible
- attention fields are editable
- all-fields panel expands
- Manual Mode reveals the old workflow

- [ ] **Step 7: Generate documents from review mode**

Click Generate Final Documents.

Expected:

- generated files are written to `outputs/`
- status log lists created files
- blank optional fields do not block generation
- server response includes any informational `missing_fields`

- [ ] **Step 8: Commit verification fixes if needed**

If verification required code fixes, commit only those fixes:

```powershell
git add weekly_review.py server.py tests/test_weekly_review.py tests/test_server_validation.py templates/index.html static/script.js static/style.css tools/export_weekly_sources.ps1 docs/automation/weekly-review-prompt.md
git commit -m "Fix weekly review verification issues"
```

If no fixes were needed, do not create an empty commit.

## Self-Review Checklist

- Spec coverage: Tasks cover reusable Codex skill creation, review JSON helpers, GUI review mode, backend endpoints, source export, skill-backed automation prompt, and verification.
- Placeholder scan: This plan intentionally avoids placeholder phrases and gives exact files, commands, snippets, and expected results.
- Type consistency: Review metadata uses `_review`; server payload uses `WeeklyReviewPayload`; review helpers use `REVIEW_META_KEY`; generated documents receive `_review`-stripped data.
