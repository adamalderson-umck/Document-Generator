# Workflow completion

- [x] Explicit main and early phases with same-week final guard and protected revisions.
- [x] Reusable Proclaim rendering integrated in main packet, with evidence-backed details and visible gaps.
- [ ] Canonical content acceptance: mechanical and selected source checks passed, but September 20 comparison found unresolved source/final editorial differences. See the canonical comparison report in the original project outputs/canonical-comparison-2026-09-20.
- [x] Commit reviewed code and instructions after tests (48b99b8).
- [ ] Replace legacy automation, verify scheduled runtime and Google access, disable old Windows export only after acceptance.

The finalized September 20 main IDML was explicitly designated by the user on September 25 and captured without altering the original. Scheduling cutover remains gated on actual scheduled-runtime evidence, not interactive connector access.

Verification: 105 tests passed, 1 existing template-identity configuration skip. All six native proofs completed and all 20 pages were visually inspected: three four-page bulletins with no reported overset/fonts/links problems, one-page Camera/Sound, six-page Proclaim. Main-stage calendar/announcements remain inherited prior-week content for human update; early drafts preserve the designated same-week final. Bulletin tab spacing and panel placement remain human cleanup as authorized. Word-unavailable handling now safely defers proof; the failed request and inactive lock were archived with explicit user approval. Main/early real-source acceptance is isolated under outputs/two-stage-acceptance and does not rewrite production documents.

Scheduled acceptance on September 25 at 14:00 reached the scheduler but failed before agent startup: `Timed out waiting for MCP response to thread/start` (18:02:10 UTC app log). No scheduled Google/build verification occurred. Production prompt and Thursday 08:00 settings were restored PAUSED; old Windows exporter remains enabled. Resume after restoring app task-start responsiveness, repeat the bounded acceptance, then activate production and retire the old exporter only on success.
