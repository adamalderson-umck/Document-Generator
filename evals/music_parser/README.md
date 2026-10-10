# Music parser evaluation tools

These optional developer tools compare music-field extraction with labeled local fixtures. They are not part of the scheduled service-packet workflow.

The schema in `grand_schema.json` is documented in `../../data_schema.md`; `../../CONTEXT.md` describes the parser terminology. The regression tests use synthetic inputs and mocked runners, so they require neither a local model server nor staff email.

Run the tests from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_music_parser_benchmark.py -q
```

Inspect the command-line interface with:

```powershell
.\.venv\Scripts\python.exe -m evals.music_parser.cli --help
```

Private labeled email fixtures, generated runs, and reports belong under the already ignored `.agent/evals/music-parser/` directory. Do not commit dated filled-in outputs alongside the reusable schema. LM Studio and command runners run only when explicitly invoked; the fake runner supports offline checks.