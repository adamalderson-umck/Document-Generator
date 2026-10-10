import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .deterministic import deterministic_parse
from .fixtures import load_fixture
from .schema import blank_output_for_source_type, schema_fields_for_source_type
from .scoring import normalize_string, score_outputs


def recovery_response_format_for_fields(source_type, fields):
    allowed_fields = set(schema_fields_for_source_type(source_type))
    unknown = sorted(field for field in fields if field not in allowed_fields)
    if unknown:
        raise ValueError(f"Unknown recovery fields: {', '.join(unknown)}")
    return {
        "type": "json_schema",
        "json_schema": {
            "name": f"music_parser_{source_type}_empty_field_recovery",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {field: {"type": "string"} for field in fields},
                "required": list(fields),
                "additionalProperties": False,
            },
        },
    }


def validate_recovery_output(value, source_type, fields):
    if not isinstance(value, dict):
        raise ValueError("Recovery output must be a JSON object")
    allowed = set(fields)
    unknown = sorted(field for field in value if field not in allowed)
    if unknown:
        raise ValueError(f"Unexpected recovery fields: {', '.join(unknown)}")
    schema_fields = set(schema_fields_for_source_type(source_type))
    invalid = sorted(field for field in fields if field not in schema_fields)
    if invalid:
        raise ValueError(f"Unknown recovery fields: {', '.join(invalid)}")

    repaired = {}
    notes = []
    for field in fields:
        if field not in value:
            repaired[field] = ""
            notes.append(f"filled missing recovery field: {field}")
            continue
        field_value = value[field]
        if field_value is None:
            repaired[field] = ""
            notes.append(f"converted null recovery field to empty string: {field}")
            continue
        if not isinstance(field_value, str):
            raise ValueError(f"Field {field} must be a string")
        repaired[field] = field_value
    return repaired, notes


def fields_to_recover(deterministic_output):
    return [field for field, value in deterministic_output.items() if normalize_string(value) == ""]


def build_recovery_prompt(fixture, deterministic_output, empty_fields):
    field_list = "\n".join(f"- {field}" for field in empty_fields)
    deterministic_json = json.dumps(deterministic_output, indent=2, ensure_ascii=False)
    return (
        "Recover missing church music fields from this recurring staff email.\n\n"
        "The deterministic parser has already filled some fields. Keep every non-empty deterministic value unchanged.\n"
        "Only evaluate the empty fields listed below. Fill an empty field only when the raw email clearly contains that exact value.\n"
        "If the email does not clearly contain the value, return an empty string.\n\n"
        "Local field rules:\n"
        "- title is the work or hymn text title, with hymn tune names removed.\n"
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
        f"Empty fields to recover:\n{field_list}\n\n"
        f"Deterministic output:\n{deterministic_json}\n\n"
        f"Raw email:\n{fixture['raw_email']}"
    )


def score_recovery_output(expected, deterministic_output, recovery_output, empty_fields):
    merged_output = dict(deterministic_output)
    summary = {
        "recoverable": 0,
        "recovered": 0,
        "missed": 0,
        "wrong_recovery": 0,
        "empty_expected": 0,
        "correct_empty": 0,
        "hallucinated": 0,
        "recovery_accuracy": 0.0,
        "hallucination_rate": 0.0,
    }
    fields = []

    for field in empty_fields:
        expected_value = normalize_string(expected.get(field, ""))
        recovered_value = normalize_string(recovery_output.get(field, ""))

        if expected_value:
            summary["recoverable"] += 1
            if recovered_value == expected_value:
                status = "recovered"
                summary["recovered"] += 1
            elif recovered_value:
                status = "wrong_recovery"
                summary["wrong_recovery"] += 1
            else:
                status = "missed"
                summary["missed"] += 1
        else:
            summary["empty_expected"] += 1
            if recovered_value:
                status = "hallucinated"
                summary["hallucinated"] += 1
            else:
                status = "correct_empty"
                summary["correct_empty"] += 1

        if recovered_value:
            merged_output[field] = recovered_value

        fields.append(
            {
                "field": field,
                "expected": expected_value,
                "deterministic_value": normalize_string(deterministic_output.get(field, "")),
                "recovered_value": recovered_value,
                "status": status,
            }
        )

    if summary["recoverable"]:
        summary["recovery_accuracy"] = round(summary["recovered"] / summary["recoverable"], 2)
    if summary["empty_expected"]:
        summary["hallucination_rate"] = round(summary["hallucinated"] / summary["empty_expected"], 2)

    return {
        "summary": summary,
        "fields": fields,
        "merged_output": merged_output,
        "merged_scoring": score_outputs(expected, merged_output),
    }


def run_recovery_fixture(fixture_path, model, runner, runs_root, repeat=1, variant=None, skip_existing=False):
    fixture = load_fixture(fixture_path)
    runs_root = Path(runs_root)
    runs_root.mkdir(parents=True, exist_ok=True)
    deterministic_output, deterministic_error = _deterministic_output(fixture)
    empty_fields = fields_to_recover(deterministic_output)
    prompt = build_recovery_prompt(fixture, deterministic_output, empty_fields)
    records = []

    for index in range(repeat):
        if skip_existing:
            existing = _find_existing_record(
                runs_root,
                fixture_id=fixture["id"],
                model=model,
                repeat_index=index,
            )
            if existing:
                records.append({**existing, "skipped": True})
                continue

        record = _run_recovery_once(
            fixture=fixture,
            model=model,
            runner=runner,
            prompt=prompt,
            deterministic_output=deterministic_output,
            deterministic_error=deterministic_error,
            empty_fields=empty_fields,
            repeat_index=index,
            variant=variant,
        )
        record_path = runs_root / _record_filename(record)
        record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        records.append({"path": str(record_path), "record": record, "skipped": False})

    return {"fixture": fixture, "records": records}


def build_recovery_report(records):
    lines = [
        "# Gemma Music Parser Empty-Field Recovery Benchmark",
        "",
        "| Model | Runs | Schema Failure Rate | Recovery Accuracy | Hallucination Rate | Recovered | Missed | Wrong | Hallucinated | Merged Accuracy | Avg Latency |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model in sorted({record.get("model", "unknown") for record in records}):
        group = [record for record in records if record.get("model") == model]
        summaries = [record.get("recovery_scoring", {}).get("summary", {}) for record in group]
        schema_failures = sum(1 for record in group if record.get("schema_status") != "ok")
        recoverable = sum(summary.get("recoverable", 0) for summary in summaries)
        recovered = sum(summary.get("recovered", 0) for summary in summaries)
        empty_expected = sum(summary.get("empty_expected", 0) for summary in summaries)
        hallucinated = sum(summary.get("hallucinated", 0) for summary in summaries)
        missed = sum(summary.get("missed", 0) for summary in summaries)
        wrong = sum(summary.get("wrong_recovery", 0) for summary in summaries)
        merged_accuracy = _mean(
            record.get("recovery_scoring", {})
            .get("merged_scoring", {})
            .get("summary", {})
            .get("non_empty_accuracy", 0)
            for record in group
        )
        lines.append(
            f"| {model} | {len(group)} | {_percent(schema_failures / len(group))} | "
            f"{_percent(recovered / recoverable if recoverable else 0)} | "
            f"{_percent(hallucinated / empty_expected if empty_expected else 0)} | "
            f"{recovered} | {missed} | {wrong} | {hallucinated} | "
            f"{_percent(merged_accuracy)} | {_mean(record.get('elapsed_seconds', 0) for record in group):.2f}s |"
        )

    lines.extend(["", "## Frequent Recovery Findings", ""])
    lines.extend(_frequent_recovery_findings(records) or ["No recovery findings."])
    return "\n".join(lines) + "\n"


def _deterministic_output(fixture):
    try:
        return deterministic_parse(fixture["raw_email"], fixture["source_type"]), None
    except Exception as exc:
        return blank_output_for_source_type(fixture["source_type"]), str(exc)


def _run_recovery_once(
    fixture,
    model,
    runner,
    prompt,
    deterministic_output,
    deterministic_error,
    empty_fields,
    repeat_index,
    variant,
):
    started_at = datetime.now(timezone.utc)
    raw_response = ""
    recovery_output = {field: "" for field in empty_fields}
    parse_status = "ok"
    schema_status = "ok"
    repair_notes = []
    diagnostics = {}
    elapsed_seconds = 0.0

    try:
        start = time.perf_counter()
        model_result = runner.run(
            fixture["source_type"],
            prompt,
            response_format=recovery_response_format_for_fields(fixture["source_type"], empty_fields),
        )
        elapsed_seconds = model_result.elapsed_seconds or (time.perf_counter() - start)
        raw_response = model_result.raw
        repair_notes.extend(model_result.repair_notes)
        diagnostics = model_result.diagnostics
        recovery_output, schema_notes = validate_recovery_output(
            model_result.parsed,
            fixture["source_type"],
            empty_fields,
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
    recovery_scoring = score_recovery_output(
        fixture["expected"],
        deterministic_output,
        recovery_output,
        empty_fields,
    )
    return {
        "workflow": "empty_field_recovery",
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
        "fields_to_recover": empty_fields,
        "deterministic_output": deterministic_output,
        "deterministic_error": deterministic_error,
        "expected_output": fixture["expected"],
        "recovery_output": recovery_output,
        "merged_output": recovery_scoring["merged_output"],
        "parse_status": parse_status,
        "schema_status": schema_status,
        "repair_notes": repair_notes,
        "diagnostics": diagnostics,
        "deterministic_scoring": score_outputs(fixture["expected"], deterministic_output),
        "recovery_scoring": recovery_scoring,
    }


def _record_filename(record):
    timestamp = record["started_at"].replace(":", "").replace("+", "z")
    return (
        f"{timestamp}-{_slug(record['fixture_id'])}-{_slug(record['model'])}-"
        f"recovery-run{record['repeat_index'] + 1}.json"
    )


def _slug(value):
    return "".join(char if char.isalnum() or char in ("-", "_") else "-" for char in value).strip("-")


def _find_existing_record(runs_root, fixture_id, model, repeat_index):
    for path in sorted(Path(runs_root).glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError):
            continue
        if record.get("workflow") != "empty_field_recovery":
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


def _mean(values):
    values = list(values)
    if not values:
        return 0
    return sum(values) / len(values)


def _percent(value):
    return f"{value * 100:.1f}%"


def _frequent_recovery_findings(records):
    counts = {}
    for record in records:
        for field in record.get("recovery_scoring", {}).get("fields", []):
            if field.get("status") in {"correct_empty"}:
                continue
            key = (field.get("field"), field.get("status"))
            counts[key] = counts.get(key, 0) + 1
    lines = []
    for (field, status), count in sorted(counts.items(), key=lambda item: -item[1])[:20]:
        lines.append(f"- {count}x `{field}` recovery status `{status}`")
    return lines
