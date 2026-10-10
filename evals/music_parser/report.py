import json
from collections import defaultdict


def build_report(records):
    lines = [
        "# Gemma Music Parser Benchmark",
        "",
        "| Model | Runs | Schema Failure Rate | Non-empty Accuracy | Missing | Mismatches | False Positives | Wrong-section | Avg Latency |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for model, model_records in sorted(_group_by_model(records).items()):
        count = len(model_records)
        schema_failures = sum(1 for record in model_records if record.get("schema_status") != "ok")
        accuracy = _mean(
            record.get("scoring", {}).get("summary", {}).get("non_empty_accuracy", 0)
            for record in model_records
        )
        missing = sum(record.get("scoring", {}).get("summary", {}).get("missing", 0) for record in model_records)
        mismatches = sum(record.get("scoring", {}).get("summary", {}).get("mismatch", 0) for record in model_records)
        false_positives = sum(
            record.get("scoring", {}).get("summary", {}).get("false_positive", 0)
            for record in model_records
        )
        wrong_sections = sum(
            len(record.get("scoring", {}).get("wrong_section_suspicions", []))
            for record in model_records
        )
        avg_latency = _mean(record.get("elapsed_seconds", 0) for record in model_records)
        lines.append(
            f"| {model} | {count} | {_percent(schema_failures / count)} | {_percent(accuracy)} | "
            f"{missing} | {mismatches} | {false_positives} | {wrong_sections} | {avg_latency:.2f}s |"
        )

    lines.extend(["", "## Repeat Stability", ""])
    repeat_lines = _repeat_stability_lines(records)
    lines.extend(repeat_lines or ["No repeated fixture/model runs found."])

    finding_lines = _field_finding_lines(records)
    if finding_lines:
        lines.extend(["", "## Field Findings", ""])
        lines.extend(finding_lines)

    return "\n".join(lines) + "\n"


def load_run_records(runs_root):
    records = []
    for path in sorted(runs_root.rglob("*.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    return records


def _group_by_model(records):
    grouped = defaultdict(list)
    for record in records:
        grouped[record.get("model", "unknown")].append(record)
    return grouped


def _mean(values):
    values = list(values)
    if not values:
        return 0
    return sum(values) / len(values)


def _percent(value):
    return f"{value * 100:.1f}%"


def _repeat_stability_lines(records):
    grouped = defaultdict(list)
    for record in records:
        grouped[(record.get("model"), record.get("fixture_id"))].append(record)

    lines = []
    for (model, fixture_id), group in sorted(grouped.items()):
        if len(group) < 2:
            continue
        serialized_outputs = {
            json.dumps(record.get("parsed_output", {}), sort_keys=True)
            for record in group
        }
        status = "stable" if len(serialized_outputs) == 1 else "varied"
        lines.append(f"- {model} / {fixture_id}: {status} across {len(group)} repeats")
    return lines


def _field_finding_lines(records):
    lines = []
    for record in records:
        label = f"{record.get('model')} / {record.get('fixture_id')}"
        for field in record.get("scoring", {}).get("fields", []):
            status = field.get("status")
            if status not in {"missing", "mismatch", "false_positive"}:
                continue
            lines.append(
                f"- {status}: {label} `{field.get('field')}` "
                f"expected `{field.get('expected')}` actual `{field.get('actual')}`"
            )
        for suspicion in record.get("scoring", {}).get("wrong_section_suspicions", []):
            lines.append(
                f"- wrong-section: {label} `{suspicion.get('value')}` expected "
                f"`{suspicion.get('expected_field')}` but appeared in `{suspicion.get('actual_field')}`"
            )
    return lines
