import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .deterministic import deterministic_parse
from .fixtures import load_fixture
from .schema import blank_output_for_source_type, schema_fields_for_source_type, validate_output_with_notes
from .scoring import score_outputs


def build_prompt(fixture):
    fields = schema_fields_for_source_type(fixture["source_type"])
    field_list = "\n".join(f"- {field}" for field in fields)
    return (
        "Extract church music fields from this recurring staff email.\n"
        "Return JSON only. Use exactly these flat string fields, and use an empty string when a field is absent.\n\n"
        "Local field rules:\n"
        "- title is the work or hymn text title, with tune names removed.\n"
        "- composer is the primary composer, melody, traditional source, or author credit.\n"
        "- details is only for secondary musical credits such as arranger, harmonizer, or editor.\n"
        "- personnel is for named guest musicians, ensembles, or performers who should be credited.\n"
        "- Do not put personnel in details.\n"
        "- Do not put bracketed rehearsal or performance instructions in any field.\n"
        "- Ignore hymn tune names: short tune identifiers often placed in parentheses after a hymn or response title, such as (HELMSLEY), (ST. MAGNUS), or (LLANGLOFFAN). They are not the title, composer, details, or personnel.\n"
        "- Ignore publisher notes, copyright notes, edition notes, hymnal numbers, lyric/text blocks, and email boilerplate.\n"
        "- A section containing only None means every field for that section is empty.\n"
        "- New Spirit Offertory credits New Spirit as personnel for the offertory.\n"
        "- A with/featuring suffix on a section header is personnel when it names a person or ensemble.\n\n"
        f"Fields:\n{field_list}\n\n"
        f"Email:\n{fixture['raw_email']}"
    )


def run_fixture(fixture_path, model, runner, runs_root, repeat=1, variant=None, skip_existing=False):
    fixture = load_fixture(fixture_path)
    runs_root = Path(runs_root)
    runs_root.mkdir(parents=True, exist_ok=True)
    records = []
    prompt = build_prompt(fixture)
    deterministic_output, deterministic_error = _deterministic_output(fixture)

    for index in range(repeat):
        if skip_existing:
            existing = _find_existing_record(
                runs_root,
                workflow=None,
                fixture_id=fixture["id"],
                model=model,
                repeat_index=index,
            )
            if existing:
                records.append({**existing, "skipped": True})
                continue

        record = _run_once(
            fixture=fixture,
            model=model,
            runner=runner,
            prompt=prompt,
            deterministic_output=deterministic_output,
            deterministic_error=deterministic_error,
            repeat_index=index,
            variant=variant,
        )
        record_path = runs_root / _record_filename(record)
        record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        records.append({"path": str(record_path), "record": record, "skipped": False})

    return {"fixture": fixture, "records": records}


def _deterministic_output(fixture):
    try:
        return deterministic_parse(fixture["raw_email"], fixture["source_type"]), None
    except Exception as exc:
        return blank_output_for_source_type(fixture["source_type"]), str(exc)


def _run_once(
    fixture,
    model,
    runner,
    prompt,
    deterministic_output,
    deterministic_error,
    repeat_index,
    variant,
):
    started_at = datetime.now(timezone.utc)
    raw_response = ""
    parsed_output = blank_output_for_source_type(fixture["source_type"])
    parse_status = "ok"
    schema_status = "ok"
    repair_notes = []
    diagnostics = {}
    elapsed_seconds = 0.0

    try:
        start = time.perf_counter()
        model_result = runner.run(fixture["source_type"], prompt)
        elapsed_seconds = model_result.elapsed_seconds or (time.perf_counter() - start)
        raw_response = model_result.raw
        repair_notes.extend(model_result.repair_notes)
        diagnostics = model_result.diagnostics
        parsed_output, schema_notes = validate_output_with_notes(
            model_result.parsed,
            fixture["source_type"],
        )
        repair_notes.extend(schema_notes)
    except json.JSONDecodeError as exc:
        parse_status = "failed"
        schema_status = "failed"
        repair_notes.append(f"JSON parse failed: {exc}")
    except Exception as exc:
        schema_status = "failed"
        repair_notes.append(str(exc))

    completed_at = datetime.now(timezone.utc)
    scoring = score_outputs(fixture["expected"], parsed_output)
    deterministic_scoring = score_outputs(fixture["expected"], deterministic_output)

    return {
        "fixture_id": fixture["id"],
        "source_type": fixture["source_type"],
        "model": model,
        "runner": getattr(runner, "name", runner.__class__.__name__.lower()),
        "variant": variant,
        "repeat_index": repeat_index,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "elapsed_seconds": round(elapsed_seconds, 4),
        "prompt": prompt,
        "raw_response": raw_response,
        "parsed_output": parsed_output,
        "deterministic_output": deterministic_output,
        "deterministic_error": deterministic_error,
        "expected_output": fixture["expected"],
        "parse_status": parse_status,
        "schema_status": schema_status,
        "repair_notes": repair_notes,
        "diagnostics": diagnostics,
        "scoring": scoring,
        "deterministic_scoring": deterministic_scoring,
    }


def _record_filename(record):
    timestamp = record["started_at"].replace(":", "").replace("+", "z")
    return (
        f"{timestamp}-{_slug(record['fixture_id'])}-{_slug(record['model'])}-"
        f"run{record['repeat_index'] + 1}.json"
    )


def _slug(value):
    return "".join(char if char.isalnum() or char in ("-", "_") else "-" for char in value).strip("-")


def _find_existing_record(runs_root, workflow, fixture_id, model, repeat_index):
    for path in sorted(Path(runs_root).glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError):
            continue
        record_workflow = record.get("workflow")
        if workflow is None and record_workflow == "advisory":
            continue
        if workflow is not None and record_workflow != workflow:
            continue
        if (
            record.get("fixture_id") == fixture_id
            and record.get("model") == model
            and record.get("repeat_index") == repeat_index
            and record.get("schema_status") == "ok"
            and record.get("parse_status") == "ok"
        ):
            return {"path": str(path), "record": record}
    return None
