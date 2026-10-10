import json
from pathlib import Path

import pytest

from evals.music_parser.cli import parse_args
from evals.music_parser.advisory import (
    advisory_response_format_for_source_type,
    run_advisory_fixture,
    score_advisory_output,
    validate_advisory_output,
)
from evals.music_parser.deterministic import canonical_from_flat_parser_output
from evals.music_parser.eval_runner import build_prompt, run_fixture
from evals.music_parser.fixtures import load_fixture, load_fixtures
from evals.music_parser.report import build_report
from evals.music_parser.recovery import (
    build_recovery_prompt,
    recovery_response_format_for_fields,
    run_recovery_fixture,
    score_recovery_output,
)
from evals.music_parser.runners import (
    FakeAdvisoryRunner,
    FakeRecoveryRunner,
    FakeRunner,
    LmStudioRunner,
    parse_model_response,
)
from evals.music_parser.schema import (
    CHOIR_SECTIONS,
    GRAND_SECTIONS,
    ORGANIST_SECTIONS,
    grand_response_format,
    grand_schema_fields,
    response_format_for_source_type,
    schema_fields_for_source_type,
)
from evals.music_parser.scoring import score_outputs


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def organist_fixture():
    return {
        "id": "organist-basic",
        "source_type": "organist",
        "raw_email": "Prelude\nHornpipe by Samuel Wesley\nOffertory\nTake Time by George Stebbins",
        "expected": {
            "prelude_title": "Hornpipe",
            "prelude_composer": "Samuel Wesley",
            "offertory_title": "Take Time",
            "offertory_composer": "George Stebbins",
        },
    }


def test_load_fixture_fills_missing_sections_and_fields(tmp_path):
    fixture_path = tmp_path / "organist.json"
    write_json(fixture_path, organist_fixture())

    fixture = load_fixture(fixture_path)

    assert fixture["id"] == "organist-basic"
    assert list(fixture["expected"].keys()) == schema_fields_for_source_type("organist")
    assert fixture["expected"]["prelude_title"] == "Hornpipe"
    assert fixture["expected"]["prelude_composer"] == "Samuel Wesley"
    assert fixture["expected"]["prelude_details"] == ""
    assert fixture["expected"]["prelude_personnel"] == ""
    assert fixture["expected"]["postlude_title"] == ""


def test_load_fixtures_reads_all_json_files_in_sorted_order(tmp_path):
    write_json(tmp_path / "b.json", {**organist_fixture(), "id": "b"})
    write_json(tmp_path / "a.json", {**organist_fixture(), "id": "a"})
    (tmp_path / "notes.txt").write_text("ignore me", encoding="utf-8")

    assert [fixture["id"] for fixture in load_fixtures(tmp_path)] == ["a", "b"]


def test_load_fixture_accepts_utf8_bom(tmp_path):
    fixture_path = tmp_path / "organist.json"
    fixture_path.write_text(json.dumps(organist_fixture()), encoding="utf-8-sig")

    fixture = load_fixture(fixture_path)

    assert fixture["id"] == "organist-basic"


def test_fixture_rejects_unknown_or_wrong_source_sections(tmp_path):
    fixture = organist_fixture()
    fixture["expected"]["anthem_title"] = "Wrong source"
    fixture_path = tmp_path / "bad.json"
    write_json(fixture_path, fixture)

    with pytest.raises(ValueError, match="anthem_title"):
        load_fixture(fixture_path)


def test_canonical_from_flat_parser_output_maps_new_spirit_to_offertory():
    flat = {
        "prelude_title": "Hornpipe",
        "prelude_composer": "Samuel Wesley",
        "new_spirit_title": "Take Time",
        "new_spirit_composer": "George Stebbins",
        "new_spirit_personnel": "New Spirit",
    }

    canonical = canonical_from_flat_parser_output(flat, "organist")

    assert list(canonical.keys()) == schema_fields_for_source_type("organist")
    assert canonical["prelude_title"] == "Hornpipe"
    assert canonical["offertory_title"] == "Take Time"
    assert canonical["offertory_composer"] == "George Stebbins"
    assert canonical["offertory_details"] == ""
    assert canonical["offertory_personnel"] == "New Spirit"


def test_response_format_uses_strict_source_specific_json_schema():
    response_format = response_format_for_source_type("choir")

    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    schema = response_format["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert schema["required"] == schema_fields_for_source_type("choir")
    assert "prelude_title" not in schema["properties"]
    assert schema["properties"]["anthem_title"] == {"type": "string"}
    assert schema["properties"]["anthem_details"] == {"type": "string"}
    assert schema["properties"]["anthem_personnel"] == {"type": "string"}


def test_grand_schema_includes_all_organist_and_choir_fields():
    fields = grand_schema_fields()

    assert GRAND_SECTIONS == ORGANIST_SECTIONS + CHOIR_SECTIONS
    assert fields == (
        schema_fields_for_source_type("organist")
        + schema_fields_for_source_type("choir")
    )
    assert schema_fields_for_source_type("combined") == fields

    response_format = grand_response_format()
    schema = response_format["json_schema"]["schema"]

    assert response_format["json_schema"]["name"] == "music_parser_grand_response"
    assert response_format["json_schema"]["strict"] is True
    assert schema["required"] == fields
    assert schema["additionalProperties"] is False
    assert schema["properties"]["prelude_title"] == {"type": "string"}
    assert schema["properties"]["anthem_personnel"] == {"type": "string"}


def test_grand_schema_json_artifact_matches_generated_response_format():
    artifact = json.loads(Path("evals/music_parser/grand_schema.json").read_text())

    assert artifact == grand_response_format()


def test_full_parser_prompt_explains_local_music_field_meanings(tmp_path):
    fixture_path = tmp_path / "organist.json"
    write_json(fixture_path, organist_fixture())
    fixture = load_fixture(fixture_path)

    prompt = build_prompt(fixture)

    assert "personnel is for named guest musicians, ensembles, or performers" in prompt
    assert "details is only for secondary musical credits" in prompt
    assert "Do not put personnel in details" in prompt
    assert "Ignore hymn tune names: short tune identifiers often placed in parentheses" in prompt
    assert "They are not the title, composer, details, or personnel" in prompt
    assert "New Spirit Offertory credits New Spirit as personnel" in prompt


def test_lmstudio_runner_posts_schema_request_and_parses_content():
    requests = []

    def fake_post_json(url, body, timeout_seconds):
        requests.append((url, body, timeout_seconds))
        return {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": json.dumps(
                            {
                                "prelude_title": "Hornpipe",
                                "prelude_composer": "Samuel Wesley",
                                "prelude_details": "",
                                "prelude_personnel": "",
                                "offertory_title": "Take Time",
                                "offertory_composer": "George Stebbins",
                                "offertory_details": "",
                                "offertory_personnel": "",
                                "communion_piece_title": "",
                                "communion_piece_composer": "",
                                "communion_piece_details": "",
                                "communion_piece_personnel": "",
                                "postlude_title": "",
                                "postlude_composer": "",
                                "postlude_details": "",
                                "postlude_personnel": "",
                                "exit_music_title": "",
                                "exit_music_composer": "",
                                "exit_music_details": "",
                                "exit_music_personnel": "",
                            }
                        )
                    },
                }
            ],
            "usage": {"total_tokens": 120},
        }

    runner = LmStudioRunner(model="gemma-4-e4b", post_json=fake_post_json)

    result = runner.run("organist", "Extract this email.")

    assert result.parsed["prelude_title"] == "Hornpipe"
    assert result.diagnostics == {"finish_reason": "stop", "total_tokens": 120}
    assert requests[0][0] == "http://localhost:1234/v1/chat/completions"
    assert requests[0][1]["model"] == "google/gemma-4-e4b"
    assert requests[0][1]["messages"] == [{"role": "user", "content": "Extract this email."}]
    assert requests[0][1]["temperature"] == 0
    assert requests[0][1]["stream"] is False
    assert requests[0][1]["response_format"]["json_schema"]["strict"] is True


def test_lmstudio_runner_accepts_advisory_response_format_override():
    requests = []

    def fake_post_json(url, body, timeout_seconds):
        requests.append(body)
        return {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": json.dumps({"prelude_title_status": "ok"})},
                }
            ]
        }

    runner = LmStudioRunner(model="gemma-4-e2b", post_json=fake_post_json)
    response_format = advisory_response_format_for_source_type("organist")

    runner.run("organist", "Review this.", response_format=response_format)

    assert requests[0]["response_format"]["json_schema"]["name"] == "music_parser_organist_advisory"


def test_parse_model_response_repairs_markdown_wrapped_json():
    parsed, notes = parse_model_response('```json\n{"prelude_title":"Hornpipe"}\n```')

    assert parsed == {"prelude_title": "Hornpipe"}
    assert notes == ["removed markdown code fence"]


def test_score_outputs_counts_field_categories_and_wrong_section():
    expected = {
        "prelude_title": "Hornpipe",
        "prelude_composer": "Samuel Wesley",
        "prelude_details": "",
        "prelude_personnel": "",
        "offertory_title": "Take Time",
        "offertory_composer": "George Stebbins",
        "offertory_details": "New Spirit",
        "offertory_personnel": "",
    }
    actual = {
        "prelude_title": "Take Time",
        "prelude_composer": "Wrong Composer",
        "prelude_details": "extra note",
        "prelude_personnel": "",
        "offertory_title": "",
        "offertory_composer": "George Stebbins",
        "offertory_details": "New Spirit",
        "offertory_personnel": "",
    }

    score = score_outputs(expected, actual)

    assert score["summary"]["match"] == 2
    assert score["summary"]["missing"] == 1
    assert score["summary"]["mismatch"] == 2
    assert score["summary"]["false_positive"] == 1
    assert score["summary"]["non_empty_accuracy"] == 0.4
    assert score["wrong_section_suspicions"] == [
        {
            "expected_field": "offertory_title",
            "actual_field": "prelude_title",
            "value": "Take Time",
        }
    ]


def test_run_fixture_with_fake_runner_writes_complete_record(tmp_path):
    fixture_path = tmp_path / "fixtures" / "organist.json"
    runs_root = tmp_path / "runs"
    write_json(fixture_path, organist_fixture())

    result = run_fixture(
        fixture_path,
        model="gemma-4-e2b",
        runner=FakeRunner(),
        runs_root=runs_root,
        repeat=2,
    )

    assert len(result["records"]) == 2
    record_path = Path(result["records"][0]["path"])
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["fixture_id"] == "organist-basic"
    assert record["model"] == "gemma-4-e2b"
    assert record["runner"] == "fake"
    assert "prompt" in record
    assert "raw_response" in record
    assert "parsed_output" in record
    assert "deterministic_output" in record
    assert "expected_output" in record
    assert "scoring" in record
    assert record["parse_status"] == "ok"
    assert record["schema_status"] == "ok"


def test_advisory_response_format_uses_field_level_status_schema():
    response_format = advisory_response_format_for_source_type("organist")
    schema = response_format["json_schema"]["schema"]

    assert response_format["json_schema"]["strict"] is True
    assert schema["additionalProperties"] is False
    assert "prelude_title_status" in schema["required"]
    assert "prelude_personnel_status" in schema["required"]
    assert schema["properties"]["prelude_title_status"] == {
        "type": "string",
        "enum": ["ok", "missing", "mismatch", "false_positive", "uncertain"],
    }
    assert schema["properties"]["prelude_title_suggested_value"] == {"type": "string"}
    assert schema["properties"]["prelude_title_reason"] == {"type": "string"}
    assert "anthem_title_status" not in schema["properties"]


def test_score_advisory_output_counts_detection_quality_and_fix_value():
    expected = {
        "prelude_title": "Hornpipe",
        "prelude_composer": "Samuel Wesley",
        "prelude_details": "",
        "offertory_title": "Take Time",
        "offertory_composer": "",
        "offertory_details": "",
    }
    deterministic = {
        "prelude_title": "",
        "prelude_composer": "Samuel Wesley",
        "prelude_details": "",
        "offertory_title": "Take Time",
        "offertory_composer": "",
        "offertory_details": "extra note",
    }
    advisory = {
        "prelude_title_status": "missing",
        "prelude_title_suggested_value": "Hornpipe",
        "prelude_title_reason": "Title appears under Prelude.",
        "prelude_composer_status": "mismatch",
        "prelude_composer_suggested_value": "Wrong",
        "prelude_composer_reason": "Bad alarm.",
        "prelude_details_status": "ok",
        "prelude_details_suggested_value": "",
        "prelude_details_reason": "",
        "offertory_title_status": "ok",
        "offertory_title_suggested_value": "Take Time",
        "offertory_title_reason": "",
        "offertory_composer_status": "ok",
        "offertory_composer_suggested_value": "",
        "offertory_composer_reason": "",
        "offertory_details_status": "false_positive",
        "offertory_details_suggested_value": "",
        "offertory_details_reason": "No extra detail present.",
    }

    score = score_advisory_output(expected, deterministic, advisory)

    assert score["summary"]["true_positive"] == 2
    assert score["summary"]["false_alarm"] == 1
    assert score["summary"]["missed_error"] == 0
    assert score["summary"]["correct_ok"] == 3
    assert score["summary"]["advisory_precision"] == 0.67
    assert score["summary"]["error_recall"] == 1.0
    assert score["summary"]["suggested_fix_accuracy"] == 1.0
    assert score["applied_scoring"]["summary"]["non_empty_accuracy"] == 0.67
    assert score["fields"][0]["truth_status"] == "missing"


def test_run_advisory_fixture_with_fake_runner_writes_complete_record(tmp_path):
    fixture_path = tmp_path / "fixtures" / "organist.json"
    runs_root = tmp_path / "runs"
    write_json(fixture_path, organist_fixture())

    result = run_advisory_fixture(
        fixture_path,
        model="gemma-4-e2b",
        runner=FakeAdvisoryRunner(),
        runs_root=runs_root,
        repeat=1,
    )

    record_path = Path(result["records"][0]["path"])
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["workflow"] == "advisory"
    assert record["fixture_id"] == "organist-basic"
    assert "deterministic_output" in record
    assert "advisory_output" in record
    assert "advisory_scoring" in record
    assert record["schema_status"] == "ok"


def test_run_advisory_fixture_skips_existing_record_when_resuming(tmp_path):
    fixture_path = tmp_path / "fixtures" / "organist.json"
    runs_root = tmp_path / "runs"
    write_json(fixture_path, organist_fixture())

    first_result = run_advisory_fixture(
        fixture_path,
        model="gemma-4-e2b",
        runner=FakeAdvisoryRunner(),
        runs_root=runs_root,
        repeat=1,
        skip_existing=True,
    )

    class ExplodingRunner:
        name = "exploding"

        def run(self, source_type, prompt, response_format=None):
            raise AssertionError("runner should not be called for existing records")

    second_result = run_advisory_fixture(
        fixture_path,
        model="gemma-4-e2b",
        runner=ExplodingRunner(),
        runs_root=runs_root,
        repeat=1,
        skip_existing=True,
    )

    assert first_result["records"][0]["path"] == second_result["records"][0]["path"]
    assert second_result["records"][0]["skipped"] is True
    assert len(list(runs_root.glob("*.json"))) == 1


def test_recovery_response_format_uses_only_empty_fields():
    response_format = recovery_response_format_for_fields(
        "organist",
        ["prelude_title", "offertory_personnel"],
    )
    schema = response_format["json_schema"]["schema"]

    assert response_format["json_schema"]["strict"] is True
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["prelude_title", "offertory_personnel"]
    assert schema["properties"]["prelude_title"] == {"type": "string"}
    assert "prelude_composer" not in schema["properties"]


def test_recovery_prompt_only_lists_empty_fields(tmp_path):
    fixture_path = tmp_path / "organist.json"
    write_json(fixture_path, organist_fixture())
    fixture = load_fixture(fixture_path)
    deterministic = {
        "prelude_title": "",
        "prelude_composer": "Samuel Wesley",
        "prelude_details": "",
        "prelude_personnel": "",
        "offertory_title": "Take Time",
        "offertory_composer": "George Stebbins",
        "offertory_details": "",
        "offertory_personnel": "",
        "communion_piece_title": "",
        "communion_piece_composer": "",
        "communion_piece_details": "",
        "communion_piece_personnel": "",
        "postlude_title": "",
        "postlude_composer": "",
        "postlude_details": "",
        "postlude_personnel": "",
        "exit_music_title": "",
        "exit_music_composer": "",
        "exit_music_details": "",
        "exit_music_personnel": "",
    }

    prompt = build_recovery_prompt(fixture, deterministic, ["prelude_title", "offertory_personnel"])

    assert "Keep every non-empty deterministic value unchanged" in prompt
    assert "Only evaluate the empty fields listed below" in prompt
    assert "- prelude_title" in prompt
    assert "- offertory_personnel" in prompt
    assert "- prelude_composer" not in prompt
    assert '"prelude_composer": "Samuel Wesley"' in prompt


def test_score_recovery_output_measures_recovered_fields_and_hallucinations():
    expected = {
        "prelude_title": "Hornpipe",
        "prelude_composer": "Samuel Wesley",
        "prelude_details": "",
        "offertory_title": "Take Time",
        "offertory_personnel": "New Spirit",
        "offertory_details": "",
    }
    deterministic = {
        "prelude_title": "",
        "prelude_composer": "Samuel Wesley",
        "prelude_details": "",
        "offertory_title": "Take Time",
        "offertory_personnel": "",
        "offertory_details": "",
    }
    recovery = {
        "prelude_title": "Hornpipe",
        "offertory_personnel": "New Spirit",
        "offertory_details": "extra note",
    }

    score = score_recovery_output(expected, deterministic, recovery, list(recovery.keys()))

    assert score["summary"]["recovered"] == 2
    assert score["summary"]["missed"] == 0
    assert score["summary"]["wrong_recovery"] == 0
    assert score["summary"]["hallucinated"] == 1
    assert score["summary"]["recovery_accuracy"] == 1.0
    assert score["merged_output"]["prelude_title"] == "Hornpipe"
    assert score["merged_scoring"]["summary"]["non_empty_accuracy"] == 1.0
    assert score["merged_scoring"]["summary"]["false_positive"] == 1


def test_run_recovery_fixture_with_fake_runner_writes_complete_record(tmp_path):
    fixture_path = tmp_path / "fixtures" / "organist.json"
    runs_root = tmp_path / "runs"
    write_json(fixture_path, organist_fixture())

    result = run_recovery_fixture(
        fixture_path,
        model="gemma-4-e2b",
        runner=FakeRecoveryRunner(),
        runs_root=runs_root,
        repeat=1,
    )

    record_path = Path(result["records"][0]["path"])
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["workflow"] == "empty_field_recovery"
    assert record["fixture_id"] == "organist-basic"
    assert "fields_to_recover" in record
    assert "deterministic_output" in record
    assert "recovery_output" in record
    assert "merged_output" in record
    assert "recovery_scoring" in record
    assert record["schema_status"] == "ok"


def test_run_recovery_fixture_skips_existing_record_when_resuming(tmp_path):
    fixture_path = tmp_path / "fixtures" / "organist.json"
    runs_root = tmp_path / "runs"
    write_json(fixture_path, organist_fixture())

    first_result = run_recovery_fixture(
        fixture_path,
        model="gemma-4-e2b",
        runner=FakeRecoveryRunner(),
        runs_root=runs_root,
        repeat=1,
        skip_existing=True,
    )

    class ExplodingRunner:
        name = "exploding"

        def run(self, source_type, prompt, response_format=None):
            raise AssertionError("runner should not be called for existing records")

    second_result = run_recovery_fixture(
        fixture_path,
        model="gemma-4-e2b",
        runner=ExplodingRunner(),
        runs_root=runs_root,
        repeat=1,
        skip_existing=True,
    )

    assert first_result["records"][0]["path"] == second_result["records"][0]["path"]
    assert second_result["records"][0]["skipped"] is True
    assert len(list(runs_root.glob("*.json"))) == 1


def test_build_report_summarizes_model_quality():
    records = [
        {
            "fixture_id": "one",
            "model": "gemma-4-e2b",
            "runner": "fake",
            "elapsed_seconds": 1.5,
            "schema_status": "ok",
            "scoring": {
                "summary": {
                    "match": 2,
                    "missing": 1,
                    "mismatch": 0,
                    "false_positive": 1,
                    "non_empty_accuracy": 0.67,
                },
                "wrong_section_suspicions": [{"expected_field": "offertory.title"}],
            },
        },
        {
            "fixture_id": "one",
            "model": "gemma-4-e2b",
            "runner": "fake",
            "elapsed_seconds": 2.5,
            "schema_status": "failed",
            "scoring": {
                "summary": {
                    "match": 1,
                    "missing": 2,
                    "mismatch": 1,
                    "false_positive": 0,
                    "non_empty_accuracy": 0.25,
                },
                "wrong_section_suspicions": [],
            },
        },
    ]

    report = build_report(records)

    assert "# Gemma Music Parser Benchmark" in report
    assert "| gemma-4-e2b | 2 | 50.0% | 46.0% | 3 | 1 | 1 | 1 | 2.00s |" in report
    assert "Repeat Stability" in report


def test_cli_parses_run_matrix_and_report_commands():
    run_args = parse_args([
        "run",
        "--fixture",
        "fixture.json",
        "--model",
        "gemma-4-e4b",
        "--runner",
        "lmstudio",
        "--repeat",
        "3",
    ])
    matrix_args = parse_args([
        "matrix",
        "--fixture-root",
        ".agent/evals/music-parser/fixtures",
        "--models",
        "gemma-4-e2b",
        "gemma-4-e4b",
        "--repeat",
        "3",
    ])
    report_args = parse_args(["report", "--runs-root", ".agent/evals/music-parser/runs"])
    advisory_matrix_args = parse_args([
        "advisory-matrix",
        "--fixture-root",
        ".agent/evals/music-parser/fixtures",
        "--models",
        "gemma-4-e2b",
        "gemma-4-e4b",
        "--repeat",
        "3",
    ])
    advisory_report_args = parse_args([
        "advisory-report",
        "--runs-root",
        ".agent/evals/music-parser/runs/advisory",
    ])
    recovery_matrix_args = parse_args([
        "recovery-matrix",
        "--fixture-root",
        ".agent/evals/music-parser/fixtures",
        "--models",
        "gemma-4-e2b",
        "gemma-4-e4b",
        "--repeat",
        "3",
    ])
    recovery_report_args = parse_args([
        "recovery-report",
        "--runs-root",
        ".agent/evals/music-parser/runs/recovery",
    ])

    assert run_args.command == "run"
    assert run_args.fixture == "fixture.json"
    assert run_args.model == "gemma-4-e4b"
    assert run_args.runner == "lmstudio"
    assert run_args.repeat == 3
    assert matrix_args.models == ["gemma-4-e2b", "gemma-4-e4b"]
    assert matrix_args.force is False
    assert report_args.command == "report"
    assert advisory_matrix_args.command == "advisory-matrix"
    assert advisory_matrix_args.models == ["gemma-4-e2b", "gemma-4-e4b"]
    assert advisory_matrix_args.force is False
    assert advisory_report_args.command == "advisory-report"
    assert recovery_matrix_args.command == "recovery-matrix"
    assert recovery_matrix_args.models == ["gemma-4-e2b", "gemma-4-e4b"]
    assert recovery_matrix_args.force is False
    assert recovery_report_args.command == "recovery-report"
