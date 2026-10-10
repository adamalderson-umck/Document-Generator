import argparse
from datetime import datetime
from pathlib import Path

from .advisory import build_advisory_report, run_advisory_fixture
from .eval_runner import run_fixture
from .fixtures import load_fixtures
from .report import build_report, load_run_records
from .recovery import build_recovery_report, run_recovery_fixture
from .runners import CommandRunner, FakeAdvisoryRunner, FakeRecoveryRunner, FakeRunner, LmStudioRunner

DEFAULT_FIXTURE_ROOT = ".agent/evals/music-parser/fixtures"
DEFAULT_RUNS_ROOT = ".agent/evals/music-parser/runs"
DEFAULT_REPORTS_ROOT = ".agent/evals/music-parser/reports"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="music-parser-benchmark")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--fixture", required=True)
    run_parser.add_argument("--model", required=True)
    run_parser.add_argument("--runner", choices=["lmstudio", "command", "fake"], default="lmstudio")
    run_parser.add_argument("--repeat", type=int, default=1)
    run_parser.add_argument("--runs-root", default=DEFAULT_RUNS_ROOT)

    matrix_parser = subparsers.add_parser("matrix")
    matrix_parser.add_argument("--fixture-root", default=DEFAULT_FIXTURE_ROOT)
    matrix_parser.add_argument("--models", nargs="+", required=True)
    matrix_parser.add_argument("--runner", choices=["lmstudio", "command", "fake"], default="lmstudio")
    matrix_parser.add_argument("--repeat", type=int, default=1)
    matrix_parser.add_argument("--runs-root", default=DEFAULT_RUNS_ROOT)
    matrix_parser.add_argument("--force", action="store_true")

    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--runs-root", default=DEFAULT_RUNS_ROOT)
    report_parser.add_argument("--reports-root", default=DEFAULT_REPORTS_ROOT)

    advisory_run_parser = subparsers.add_parser("advisory-run")
    advisory_run_parser.add_argument("--fixture", required=True)
    advisory_run_parser.add_argument("--model", required=True)
    advisory_run_parser.add_argument("--runner", choices=["lmstudio", "command", "fake"], default="lmstudio")
    advisory_run_parser.add_argument("--repeat", type=int, default=1)
    advisory_run_parser.add_argument("--runs-root", default=DEFAULT_RUNS_ROOT)

    advisory_matrix_parser = subparsers.add_parser("advisory-matrix")
    advisory_matrix_parser.add_argument("--fixture-root", default=DEFAULT_FIXTURE_ROOT)
    advisory_matrix_parser.add_argument("--models", nargs="+", required=True)
    advisory_matrix_parser.add_argument("--runner", choices=["lmstudio", "command", "fake"], default="lmstudio")
    advisory_matrix_parser.add_argument("--repeat", type=int, default=1)
    advisory_matrix_parser.add_argument("--runs-root", default=DEFAULT_RUNS_ROOT)
    advisory_matrix_parser.add_argument("--force", action="store_true")

    advisory_report_parser = subparsers.add_parser("advisory-report")
    advisory_report_parser.add_argument("--runs-root", default=DEFAULT_RUNS_ROOT)
    advisory_report_parser.add_argument("--reports-root", default=DEFAULT_REPORTS_ROOT)

    recovery_run_parser = subparsers.add_parser("recovery-run")
    recovery_run_parser.add_argument("--fixture", required=True)
    recovery_run_parser.add_argument("--model", required=True)
    recovery_run_parser.add_argument("--runner", choices=["lmstudio", "command", "fake"], default="lmstudio")
    recovery_run_parser.add_argument("--repeat", type=int, default=1)
    recovery_run_parser.add_argument("--runs-root", default=DEFAULT_RUNS_ROOT)

    recovery_matrix_parser = subparsers.add_parser("recovery-matrix")
    recovery_matrix_parser.add_argument("--fixture-root", default=DEFAULT_FIXTURE_ROOT)
    recovery_matrix_parser.add_argument("--models", nargs="+", required=True)
    recovery_matrix_parser.add_argument("--runner", choices=["lmstudio", "command", "fake"], default="lmstudio")
    recovery_matrix_parser.add_argument("--repeat", type=int, default=1)
    recovery_matrix_parser.add_argument("--runs-root", default=DEFAULT_RUNS_ROOT)
    recovery_matrix_parser.add_argument("--force", action="store_true")

    recovery_report_parser = subparsers.add_parser("recovery-report")
    recovery_report_parser.add_argument("--runs-root", default=DEFAULT_RUNS_ROOT)
    recovery_report_parser.add_argument("--reports-root", default=DEFAULT_REPORTS_ROOT)

    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.command == "run":
        result = run_fixture(
            args.fixture,
            model=args.model,
            runner=_build_runner(args.runner, args.model),
            runs_root=args.runs_root,
            repeat=args.repeat,
        )
        for record in result["records"]:
            print(record["path"])
        return 0

    if args.command == "matrix":
        for fixture in load_fixtures(args.fixture_root):
            for model in args.models:
                result = run_fixture(
                    fixture["fixture_path"],
                    model=model,
                    runner=_build_runner(args.runner, model),
                    runs_root=args.runs_root,
                    repeat=args.repeat,
                    skip_existing=not args.force,
                )
                for record in result["records"]:
                    print(_format_record_path(record))
        return 0

    if args.command == "report":
        runs_root = Path(args.runs_root)
        reports_root = Path(args.reports_root)
        reports_root.mkdir(parents=True, exist_ok=True)
        report = build_report(load_run_records(runs_root))
        report_path = reports_root / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-report.md"
        report_path.write_text(report, encoding="utf-8")
        print(report_path)
        return 0

    if args.command == "advisory-run":
        result = run_advisory_fixture(
            args.fixture,
            model=args.model,
            runner=_build_advisory_runner(args.runner, args.model),
            runs_root=args.runs_root,
            repeat=args.repeat,
        )
        for record in result["records"]:
            print(record["path"])
        return 0

    if args.command == "advisory-matrix":
        for fixture in load_fixtures(args.fixture_root):
            for model in args.models:
                result = run_advisory_fixture(
                    fixture["fixture_path"],
                    model=model,
                    runner=_build_advisory_runner(args.runner, model),
                    runs_root=args.runs_root,
                    repeat=args.repeat,
                    skip_existing=not args.force,
                )
                for record in result["records"]:
                    print(_format_record_path(record))
        return 0

    if args.command == "advisory-report":
        runs_root = Path(args.runs_root)
        reports_root = Path(args.reports_root)
        reports_root.mkdir(parents=True, exist_ok=True)
        report = build_advisory_report(load_run_records(runs_root))
        report_path = reports_root / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-advisory-report.md"
        report_path.write_text(report, encoding="utf-8")
        print(report_path)
        return 0

    if args.command == "recovery-run":
        result = run_recovery_fixture(
            args.fixture,
            model=args.model,
            runner=_build_recovery_runner(args.runner, args.model),
            runs_root=args.runs_root,
            repeat=args.repeat,
        )
        for record in result["records"]:
            print(record["path"])
        return 0

    if args.command == "recovery-matrix":
        for fixture in load_fixtures(args.fixture_root):
            for model in args.models:
                result = run_recovery_fixture(
                    fixture["fixture_path"],
                    model=model,
                    runner=_build_recovery_runner(args.runner, model),
                    runs_root=args.runs_root,
                    repeat=args.repeat,
                    skip_existing=not args.force,
                )
                for record in result["records"]:
                    print(_format_record_path(record))
        return 0

    if args.command == "recovery-report":
        runs_root = Path(args.runs_root)
        reports_root = Path(args.reports_root)
        reports_root.mkdir(parents=True, exist_ok=True)
        report = build_recovery_report(load_run_records(runs_root))
        report_path = reports_root / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-recovery-report.md"
        report_path.write_text(report, encoding="utf-8")
        print(report_path)
        return 0

    raise ValueError(f"Unknown command: {args.command}")


def _build_runner(runner_name, model):
    if runner_name == "lmstudio":
        return LmStudioRunner(model=model)
    if runner_name == "command":
        return CommandRunner(model=model)
    if runner_name == "fake":
        return FakeRunner()
    raise ValueError(f"Unknown runner: {runner_name}")


def _build_advisory_runner(runner_name, model):
    if runner_name == "lmstudio":
        return LmStudioRunner(model=model)
    if runner_name == "command":
        return CommandRunner(model=model)
    if runner_name == "fake":
        return FakeAdvisoryRunner()
    raise ValueError(f"Unknown runner: {runner_name}")


def _build_recovery_runner(runner_name, model):
    if runner_name == "lmstudio":
        return LmStudioRunner(model=model)
    if runner_name == "command":
        return CommandRunner(model=model)
    if runner_name == "fake":
        return FakeRecoveryRunner()
    raise ValueError(f"Unknown runner: {runner_name}")


def _format_record_path(record):
    prefix = "SKIP" if record.get("skipped") else "RUN"
    return f"{prefix} {record['path']}"


if __name__ == "__main__":
    raise SystemExit(main())
