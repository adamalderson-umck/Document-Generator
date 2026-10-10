import re

from .schema import SECTION_FIELDS


def normalize_string(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _split_field_key(field):
    for suffix in SECTION_FIELDS:
        suffix_text = f"_{suffix}"
        if field.endswith(suffix_text):
            return field[: -len(suffix_text)], suffix
    return field, ""


def score_outputs(expected, actual):
    ordered_fields = list(expected.keys())
    for field in sorted(actual.keys()):
        if field not in expected:
            ordered_fields.append(field)

    summary = {
        "match": 0,
        "missing": 0,
        "mismatch": 0,
        "false_positive": 0,
        "expected_non_empty": 0,
        "non_empty_accuracy": 0.0,
    }
    fields = []

    for field in ordered_fields:
        expected_value = normalize_string(expected.get(field, ""))
        actual_value = normalize_string(actual.get(field, ""))

        if expected_value:
            summary["expected_non_empty"] += 1

        if expected_value and actual_value == expected_value:
            status = "match"
            summary["match"] += 1
        elif expected_value and not actual_value:
            status = "missing"
            summary["missing"] += 1
        elif expected_value and actual_value:
            status = "mismatch"
            summary["mismatch"] += 1
        elif not expected_value and actual_value:
            status = "false_positive"
            summary["false_positive"] += 1
        else:
            status = "empty"

        fields.append(
            {
                "field": field,
                "expected": expected_value,
                "actual": actual_value,
                "status": status,
            }
        )

    if summary["expected_non_empty"]:
        summary["non_empty_accuracy"] = round(
            summary["match"] / summary["expected_non_empty"],
            2,
        )

    return {
        "summary": summary,
        "fields": fields,
        "wrong_section_suspicions": _wrong_section_suspicions(expected, actual),
    }


def _wrong_section_suspicions(expected, actual):
    normalized_actual = {
        field: normalize_string(value)
        for field, value in actual.items()
        if normalize_string(value)
    }
    suspicions = []

    for expected_field, expected_value in expected.items():
        normalized_expected = normalize_string(expected_value)
        if not normalized_expected:
            continue

        expected_section, _ = _split_field_key(expected_field)
        for actual_field, actual_value in normalized_actual.items():
            actual_section, _ = _split_field_key(actual_field)
            if expected_section == actual_section:
                continue
            if actual_value == normalized_expected:
                suspicions.append(
                    {
                        "expected_field": expected_field,
                        "actual_field": actual_field,
                        "value": normalized_expected,
                    }
                )
                break

    return suspicions
