import json
from pathlib import Path

from .schema import normalize_source_type, validate_output_with_notes


def load_fixture(path):
    path = Path(path)
    raw_fixture = json.loads(path.read_text(encoding="utf-8-sig"))

    fixture_id = raw_fixture.get("id")
    if not isinstance(fixture_id, str) or not fixture_id.strip():
        raise ValueError(f"Fixture {path} must include a non-empty string id")

    source_type = normalize_source_type(raw_fixture.get("source_type"))
    raw_email = raw_fixture.get("raw_email")
    if not isinstance(raw_email, str):
        raise ValueError(f"Fixture {path} must include raw_email as a string")

    expected = raw_fixture.get("expected")
    if not isinstance(expected, dict):
        raise ValueError(f"Fixture {path} must include expected as an object")

    expected_output, repair_notes = validate_output_with_notes(expected, source_type)
    return {
        "id": fixture_id,
        "source_type": source_type,
        "raw_email": raw_email,
        "expected": expected_output,
        "fixture_path": str(path),
        "fixture_repair_notes": repair_notes,
    }


def load_fixtures(root):
    root = Path(root)
    if root.is_file():
        return [load_fixture(root)]
    return [load_fixture(path) for path in sorted(root.rglob("*.json"))]
