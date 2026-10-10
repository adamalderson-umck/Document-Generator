import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .deterministic import deterministic_parse
from .fixtures import load_fixture
from .schema import blank_output_for_source_type, schema_fields_for_source_type
from .scoring import normalize_string, score_outputs

ADVISORY_STATUSES = ["ok", "missing", "mismatch", "false_positive", "uncertain"]
ACTIONABLE_STATUSES = {"missing", "mismatch", "false_positive"}


def advisory_response_format_for_source_type(source_type):
    fields = schema_fields_for_source_type(source_type)
    properties = {}
    required = []
    for field in fields:
        status_key = f"{field}_status"
        suggested_key = f"{field}_suggested_value"
        reason_key = f"{field}_reason"
        properties[status_key] = {"type": "string", "enum": ADVISORY_STATUSES}
        properties[suggested_key] = {"type": "string"}
        properties[reason_key] = {"type": "string"}
        required.extend([status_key, suggested_key, reason_key])

    return {
        "type": "json_schema",
        "json_schema": {
            "name": f"music_parser_{source_type}_advisory",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


def validate_advisory_output(value, source_type):
    if not isinstance(value, dict):
        raise ValueError("Advisory output must be a JSON object")

    fields = schema_fields_for_source_type(source_type)
    allowed = {
        key
        for field in fields
        for key in (
            f"{field}_status",
            f"{field}_suggested_value",
            f"{field}_reason",
        )
    }
    unknown = sorted(key for key in value if key not in allowed)
    if unknown:
        raise ValueError(f"Unexpected advisory fields: {', '.join(unknown)}")

    repaired = {}
    notes = []
    for field in fields:
        status_key = f"{field}_status"
        suggested_key = f"{field}_suggested_value"
        reason_key = f"{field}_reason"

        status = value.get(status_key)
        if status is None:
            status = "uncertain"
            notes.append(f"filled missing status: {field}")
        if status not in ADVISORY_STATUSES:
            raise ValueError(f"Invalid advisory status for {field}: {status}")
        repaired[status_key] = status

        for key in (suggested_key, reason_key):
            field_value = value.get(key, "")
            if field_value is None:
                field_value = ""
                notes.append(f"converted null field to empty string: {key}")
            if not isinstance(field_value, str):
                raise ValueError(f"Field {key} must be a string")
            repaired[key] = field_value

    return repaired, notes


def build_advisory_prompt(fixture, deterministic_output):
    fields = schema_fields_for_source_type(fixture["source_type"])
    field_list = "\n".join(f"- {field}" for field in fields)
    deterministic_json = json.dumps(deterministic_output, indent=2, ensure_ascii=False)
    return (
        "Review the deterministic church music parser output against the raw email.\n"
        "Do not produce a fresh parse. Evaluate each field in the deterministic output.\n"
        "Use status ok when the deterministic value is correct.\n"
        "Use missing when the deterministic value is empty but the email contains that field.\n"
        "Use mismatch when the deterministic value is non-empty but different from the email.\n"
        "Use false_positive when the deterministic value is non-empty but the email does not contain that field.\n"
        "Use uncertain only when the email does not provide enough evidence.\n"
        "For suggested_value, provide the corrected value. For ok, repeat the deterministic value. "
        "For false_positive, use an empty string.\n"
        "Return JSON only.\n\n"
        f"Fields:\n{field_list}\n\n"
        f"Deterministic output:\n{deterministic_json}\n\n"
        f"Raw email:\n{fixture['raw_email']}"
    )


def score_advisory_output(expected, deterministic_output, advisory_output):
    fields = list(expected.keys())
    scored_fields = []
    summary = {
        "true_positive": 0,
        "false_alarm": 0,
        "missed_error": 0,
        "correct_ok": 0,
        "status_match": 0,
        "correct_suggestion": 0,
        "total_errors": 0,
        "total_ok": 0,
        "advisory_precision": 0.0,
        "error_recall": 0.0,
        "ok_specificity": 0.0,
        "status_accuracy": 0.0,
        "suggested_fix_accuracy": 0.0,
    }
    applied_output = dict(deterministic_output)

    for field in fields:
        truth_status = _truth_status(expected.get(field, ""), deterministic_output.get(field, ""))
        model_status = advisory_output.get(f"{field}_status", "uncertain")
        suggested_value = advisory_output.get(f"{field}_suggested_value", "")
        reason = advisory_output.get(f"{field}_reason", "")
        truth_is_error = truth_status != "ok"
        model_flags = model_status != "ok"

        if truth_is_error:
            summary["total_errors"] += 1
        else:
            summary["total_ok"] += 1

        if model_status == truth_status:
            summary["status_match"] += 1

        if truth_is_error and model_flags:
            summary["true_positive"] += 1
            if normalize_string(suggested_value) == normalize_string(expected.get(field, "")):
                summary["correct_suggestion"] += 1
        elif truth_is_error and not model_flags:
            summary["missed_error"] += 1
        elif not truth_is_error and model_flags:
            summary["false_alarm"] += 1
        else:
            summary["correct_ok"] += 1

        if model_status in ACTIONABLE_STATUSES:
            applied_output[field] = suggested_value

        scored_fields.append(
            {
                "field": field,
                "truth_status": truth_status,
                "advisory_status": model_status,
                "deterministic_value": normalize_string(deterministic_output.get(field, "")),
                "expected": normalize_string(expected.get(field, "")),
                "suggested_value": normalize_string(suggested_value),
                "reason": reason,
            }
        )

    flagged = summary["true_positive"] + summary["false_alarm"]
    if flagged:
        summary["advisory_precision"] = round(summary["true_positive"] / flagged, 2)
    if summary["total_errors"]:
        summary["error_recall"] = round(summary["true_positive"] / summary["total_errors"], 2)
    if summary["total_ok"]:
        summary["ok_specificity"] = round(summary["correct_ok"] / summary["total_ok"], 2)
    if fields:
        summary["status_accuracy"] = round(summary["status_match"] / len(fields), 2)
    if summary["true_positive"]:
        summary["suggested_fix_accuracy"] = round(
            summary["correct_suggestion"] / summary["true_positive"],
            2,
        )

    return {
        "summary": summary,
        "fields": scored_fields,
        "applied_output": applied_output,
        "applied_scoring": score_outputs(expected, applied_output),
    }


def run_advisory_fixture(
    fixture_path,
    model,
    runner,
    runs_root,
    repeat=1,
    variant=None,
    skip_existing=False,
):
    fixture = load_fixture(fixture_path)
    runs_root = Path(runs_root)
    runs_root.mkdir(parents=True, exist_ok=True)
    deterministic_output, deterministic_error = _deterministic_output(fixture)
    prompt = build_advisory_prompt(fixture, deterministic_output)
    records = []

    for index in range(repeat):
        if skip_existing:
            existing = _find_existing_record(
                runs_root,
                workflow="advisory",
                fixture_id=fixture["id"],
                model=model,
                repeat_index=index,
            )
            if existing:
                records.append({**existing, "skipped": True})
                continue

        record = _run_advisory_once(
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


def build_advisory_report(records):
    lines = [
        "# Gemma Music Parser Advisory Benchmark",
        "",
        "| Model | Runs | Schema Failure Rate | Error Recall | Precision | False Alarms | Missed Errors | Suggested Fix Accuracy | Applied Accuracy | Avg Latency |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model in sorted({record.get("model", "unknown") for record in records}):
        group = [record for record in records if record.get("model") == model]
        count = len(group)
        schema_failures = sum(1 for record in group if record.get("schema_status") != "ok")
        summaries = [record.get("advisory_scoring", {}).get("summary", {}) for record in group]
        false_alarms = sum(summary.get("false_alarm", 0) for summary in summaries)
        missed_errors = sum(summary.get("missed_error", 0) for summary in summaries)
        lines.append(
            f"| {model} | {count} | {_percent(schema_failures / count)} | "
            f"{_percent(_weighted_rate(summaries, 'true_positive', 'total_errors'))} | "
            f"{_percent(_weighted_rate(summaries, 'true_positive', None, 'false_alarm'))} | "
            f"{false_alarms} | {missed_errors} | "
            f"{_percent(_weighted_rate(summaries, 'correct_suggestion', 'true_positive'))} | "
            f"{_percent(_mean(record.get('advisory_scoring', {}).get('applied_scoring', {}).get('summary', {}).get('non_empty_accuracy', 0) for record in group))} | "
            f"{_mean(record.get('elapsed_seconds', 0) for record in group):.2f}s |"
        )

    lines.extend(["", "## Frequent Findings", ""])
    lines.extend(_frequent_advisory_findings(records) or ["No advisory findings."])
    return "\n".join(lines) + "\n"


def _deterministic_output(fixture):
    try:
        return deterministic_parse(fixture["raw_email"], fixture["source_type"]), None
    except Exception as exc:
        return blank_output_for_source_type(fixture["source_type"]), str(exc)


def _run_advisory_once(
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
    advisory_output = _uncertain_advisory_output(fixture["source_type"], deterministic_output)
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
            response_format=advisory_response_format_for_source_type(fixture["source_type"]),
        )
        elapsed_seconds = model_result.elapsed_seconds or (time.perf_counter() - start)
        raw_response = model_result.raw
        repair_notes.extend(model_result.repair_notes)
        diagnostics = model_result.diagnostics
        advisory_output, schema_notes = validate_advisory_output(
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
    deterministic_scoring = score_outputs(fixture["expected"], deterministic_output)
    advisory_scoring = score_advisory_output(
        fixture["expected"],
        deterministic_output,
        advisory_output,
    )
    return {
        "workflow": "advisory",
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
        "deterministic_output": deterministic_output,
        "deterministic_error": deterministic_error,
        "expected_output": fixture["expected"],
        "advisory_output": advisory_output,
        "parse_status": parse_status,
        "schema_status": schema_status,
        "repair_notes": repair_notes,
        "diagnostics": diagnostics,
        "deterministic_scoring": deterministic_scoring,
        "advisory_scoring": advisory_scoring,
    }


def _truth_status(expected_value, deterministic_value):
    expected_value = normalize_string(expected_value)
    deterministic_value = normalize_string(deterministic_value)
    if expected_value == deterministic_value:
        return "ok"
    if expected_value and not deterministic_value:
        return "missing"
    if not expected_value and deterministic_value:
        return "false_positive"
    return "mismatch"


def _uncertain_advisory_output(source_type, deterministic_output):
    advisory = {}
    for field in schema_fields_for_source_type(source_type):
        advisory[f"{field}_status"] = "uncertain"
        advisory[f"{field}_suggested_value"] = deterministic_output.get(field, "")
        advisory[f"{field}_reason"] = ""
    return advisory


def _record_filename(record):
    timestamp = record["started_at"].replace(":", "").replace("+", "z")
    return (
        f"{timestamp}-{_slug(record['fixture_id'])}-{_slug(record['model'])}-"
        f"advisory-run{record['repeat_index'] + 1}.json"
    )


def _slug(value):
    return "".join(char if char.isalnum() or char in ("-", "_") else "-" for char in value).strip("-")


def _find_existing_record(runs_root, workflow, fixture_id, model, repeat_index):
    for path in sorted(Path(runs_root).glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError):
            continue
        if record.get("workflow") != workflow:
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


def _weighted_rate(summaries, numerator_key, denominator_key=None, extra_denominator_key=None):
    numerator = sum(summary.get(numerator_key, 0) for summary in summaries)
    if denominator_key:
        denominator = sum(summary.get(denominator_key, 0) for summary in summaries)
    else:
        denominator = numerator + sum(summary.get(extra_denominator_key, 0) for summary in summaries)
    if not denominator:
        return 0
    return numerator / denominator


def _frequent_advisory_findings(records):
    counts = {}
    for record in records:
        for field in record.get("advisory_scoring", {}).get("fields", []):
            if field.get("advisory_status") == "ok":
                continue
            key = (field.get("field"), field.get("truth_status"), field.get("advisory_status"))
            counts[key] = counts.get(key, 0) + 1
    lines = []
    for (field, truth_status, advisory_status), count in sorted(counts.items(), key=lambda item: -item[1])[:20]:
        lines.append(f"- {count}x `{field}` truth `{truth_status}`, advisory `{advisory_status}`")
    return lines
