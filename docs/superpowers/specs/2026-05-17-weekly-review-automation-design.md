# Weekly Review Automation Design

## Purpose

Document Generator should move from manual upload and pasted email parsing toward a weekly Codex-prepared review packet. The Friday automation will gather the same recurring church planning inputs the user already receives, extract the fields needed by the current templates, and leave a generator-ready JSON file for review in the GUI.

The goal is not full unattended document production. The goal is a reliable "prepare, review, generate" workflow where Codex handles extraction and the user keeps the final production click.

## Current System

The app currently has these working pieces:

- `parse_source_doc()` extracts service data from a source `.docx`.
- `parse_email_text()` extracts music data from pasted organist and choir emails.
- `get_missing_variables()` compares accumulated data to variables used in `docx_templates/`.
- `generate_word_docs()` renders all local templates into `outputs/`.
- The GUI stores parsed data in a session, asks for missing fields, then calls `/generate_final`.

The new workflow should reuse `generate_word_docs()` and the template-variable discovery path. The extraction front door changes from manual upload/paste to a weekly review JSON.

## Target Workflow

Every Friday morning, a Codex automation targets the upcoming Sunday.

1. Determine the upcoming Sunday service date from the automation run date.
2. Search the local Outlook PST store `Adam Alderson`.
3. Find the source worship-notes email in `Inbox\Staff\Nathan` using the subject marker `[Month] [DD] worship notes`, such as `May 24 worship notes`.
4. Select the `10:30` `.docx` attachment from that email.
5. Search music emails in `Inbox\Music` for the week preceding the service date.
6. Extract values for the variables used by the current templates.
7. Write a review JSON file to `inputs/weekly_reviews/YYYY-MM-DD-review.json`, where the date is the target service date.
8. Leave final document generation to the GUI.

If the Nathan email or `10:30` attachment cannot be found, the automation should fall back to the newest plausible `.docx` already in `inputs/` and record that fallback in `_review`.

Special mid-week services are out of scope for the recurring automation. They remain one-off workflows.

## Review JSON Shape

The review file should be directly usable by the generator. Top-level keys are the variables used by the current templates, plus a `_review` object.

Example shape:

```json
{
  "date": "May 24, 2026",
  "service_time": "10:30 am",
  "sunday_title": "Day of Pentecost",
  "hymn_1_num": "UMH 465",
  "hymn_1_title": "Holy Spirit, Truth Divine",
  "prelude_title": "Example",
  "_review": {
    "target_service_date": "2026-05-24",
    "status": "needs_review",
    "sources": [],
    "attention_fields": [],
    "missing_usual_fields": [],
    "low_confidence_fields": [],
    "conflicts": [],
    "notes": []
  }
}
```

Top-level values should be strings unless an existing template variable already expects a boolean, such as `is_communion_sunday`.

Blank values are allowed. Many fields are normally empty, and blanks must not block generation.

## Attention Model

The GUI should not ask the user to acknowledge every blank optional field. It should focus attention on fields that deserve a look.

Attention fields include:

- conflicting evidence from multiple messages
- low-confidence extraction
- a value that appears structurally odd, such as a hymn title with no hymn number
- a field from the small "usually present" set that is blank
- source-selection problems, such as no matching Nathan email or multiple `10:30` attachments

Version 1 should use a simple hardcoded "usually present" set. Later versions can add history-based warnings from previous weekly review JSONs.

## GUI Changes

The GUI becomes a review console when a weekly review JSON exists.

On load, the backend should expose the newest file in `inputs/weekly_reviews/`. The first screen should show:

- target service date
- source summary
- attention fields with editable values
- a Generate button

There should also be an expandable all-fields view for complete review and editing.

The existing upload and pasted-email workflow can remain available as a fallback/manual mode, but it should no longer be the primary path when a current weekly review exists.

Generation should not be blocked by blank fields. Clicking Generate sends the reviewed JSON to the backend, merges site config, and calls the existing `generate_word_docs()` path.

## Backend Changes

Add endpoints or equivalent server functions for:

- listing weekly review files
- loading the latest weekly review
- saving edits to a review JSON
- generating documents from a review JSON

Generation from a review file should reuse existing validation behavior where useful:

- merge `site_config.local.json`
- apply hymn-number formatting when users edit hymn-number fields
- run `get_missing_variables()` only as an informational warning, not a blocker
- call `generate_word_docs()`
- report generated file paths in the GUI status log

## Automation Behavior

The recurring Codex automation should run Friday mornings and write the review packet only. It should not generate final documents.

The prompt for the automation should be self-contained:

- workspace path
- PST/store name and relevant folders
- target date rule: upcoming Sunday
- source-doc search rule: Nathan folder subject `[Month] [DD] worship notes`
- source attachment rule: `10:30` `.docx`
- music email rule: `Inbox\Music`, week preceding service
- output path rule: `inputs/weekly_reviews/YYYY-MM-DD-review.json`
- terminology rule: use `CONTEXT.md`
- schema rule: include current template variables plus `_review`

The automation should record enough source metadata in `_review.sources` to make the extraction auditable without dumping unnecessary full email bodies into the review file.

## Privacy And Local Data

Weekly review JSON files live under `inputs/weekly_reviews/`, inside the already git-ignored `inputs/` area. They may contain church-specific planning data and should remain local.

Attachments saved for extraction should live in a local ignored temp/cache path, or be copied into `inputs/` only when needed for review. Generated documents remain in `outputs/`.

## Testing And Verification

Implementation should include tests for:

- detecting current template variables
- loading and saving weekly review JSON files
- attention-field classification
- generation from a review JSON
- fallback behavior when source email or attachment is missing

Manual verification should include the known May 17, 2026 sample:

- Nathan email subject `May 17 worship notes`
- attachment `Ascension Sunday 1030am.docx`
- music emails from the preceding week
- output review JSON containing current template variables plus `_review`

## Open Decisions

No blocking decisions remain for the spec. Future implementation can refine:

- exact hardcoded "usually present" field set
- detailed `_review.sources` metadata shape
- whether old weekly reviews should be archived, hidden, or simply listed
