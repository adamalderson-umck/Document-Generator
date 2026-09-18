# Service packet acceptance inventory

## Execution status

Implementation is running inline in the manually owned `codex/weekly-service-packet` worktree, created from fetched `origin/main` at `1747ff36cb84dfeeef71b72b123be4166a1635aa`. The original checkout is untouched. Approved plan/spec copies were hash-verified; they remain local ignored planning files.

- Task 1: fixture inventory in progress; required early-service sources remain unavailable in searched local locations.
- Task 2: initial reusable model/source/IDML/technical/build helpers and main replay generated; not accepted as finished until native composition and visual review pass. Layout refinements remain possible.
- Tasks 3–8: not started. No native application calls or schedule changes.

## Local fixtures

Ten originals were copied to ignored `inputs/service_packets/acceptance/`, with matching SHA-256 values recorded in `manifest.json`. These include the labeled template, exported finalized September 6 main baseline, both technical templates, both main-service Nathan orders, and saved source/export metadata for September 6 and 13. Original paths and private content are deliberately excluded from this document.

September 13 is the first main-service replay: the supplied order identifies a 10:00 service, and the saved music messages explicitly establish combined service and band offertory. The previous week's finalized main baseline export is available. The order—not the old generated bulletin—controls sequence. In particular, additional closing music from other sources must be treated as a structural discrepancy unless supported by an authorized correction.

September 6 main Communion order is available. The export status reports zero Nathan attachments, despite a successful collector result. September 13 reports one source message but zero saved attachments; its named attachment was supplied separately. Therefore collector success is not source completeness.

The local input/output/scratch inventory and worship-related Downloads DOCX inventory did not locate the September 6 early-service orders. Existing early-service finished INDD/PDF files are comparison evidence, not replacement orders. Ordinary three-service acceptance remains unrun pending actual source discovery or supply. Google source snapshots and a prior-week baseline for the Communion replay still need to be established.

## Observed IDML contract

- Both template and finalized-main export contain text-frame labels `worship_order` and `service_heading`.
- Opaque story identities differ: template order/header are `u10c`/`u231`; finalized export uses `u131`/`u153`. Resolve through labels and ParentStory, never fixed IDs.
- Order frames are threaded; retain NextTextFrame and geometry unchanged.
- Observed styles: `OOW Body` at 12 pt, `OOW Body--Indented`, `OOW Heading`, `Liturgical Sunday` at 22 pt, `Date and Time` at 18 pt and `Text Benediction`. Indented/heading styles inherit properties; resolve inherited values before selecting compact treatments.
- Non-order stories include calendar, personnel, flowers and welcome copy. They remain inherited and explicitly unverified for the new service.

## Observed technical documents

Camera template: 35 rows, five columns (`Worship Element`, `CAM 1`, `Balcony C`, `Balcony L`, `Proclaim`). Sound template: 35 rows, two columns (`Scene`, `Worship Element`) and separate operator instructions. Both currently hard-code 10:30 in their headers. The new renderer must use actual time and dynamic rows; it must not retain a fixed organ assignment for band offertories.

Existing cue cells are candidate conventions only. Unknown assignments remain review markers until supported by source evidence or confirmed conventions.

## Native acceptance boundary

Registry inspection found `InDesign.Application.2025`, `.2026` and `Word.Application.16` registrations. Registration is not proof of successful automation, installed fonts or safe focus behavior. No native application was opened or selected.

Before the first composition test: agree on a safe moment, verify refusal while user documents are open, then test scratch-only composition with applications available. Verify owned-handle cleanup/preferences and focus behavior. Inspect all bulletin and technical proof pages. Background proofing remains unverified until this passes.

## Verification log

- Clean-worktree existing suite: 39 passed, 1 skipped. Executed with the existing repository virtual environment, without modifying it.
- Source snapshot copies: all ten SHA-256 checks passed.
- New helper tests: 22 passed after observed initial failures. Combined suite: 61 passed, 1 skipped.
- September 13 replay generated under `outputs/2026-09-13/rev-001/`: `1000-bulletin.idml`, `1000-cameras.docx`, `1000-sound.docx`, manifest, accepted source representation and review report. This is an isolated historical acceptance replay, not a production weekly run.
- IDML XML parsed successfully. Exactly the two labeled story members changed; every unrelated package member is byte-identical to the frozen baseline.
- Camera and Sound both contain the same 17 ordered source items and actual 10:00 header. Unknown cue assignments are visibly marked. Historic cue conventions are not yet confirmed.
- The organist's postlude and choir prayer response are absent from Nathan's order, so both remain reported structural discrepancies rather than automatic insertions.
- Native proofing, visual fidelity/fit, real three-service replay and scheduled runtime remain unverified. No native application was opened or selected.

## Next checkpoint

Task 3 requires a user-agreed safe moment before native application testing. First verify refusal when a user document is open, then test generated scratch files only with the relevant app available. Never open/switch/close a user's document. Until then, all three replay artifacts remain `proof_status: pending`.

Remaining implementation includes native proof adapters, robust cross-output/editorial validation, three-service Google routing, bounded fit repair, finalization, jobs/recovery, skills and scheduling. The initial builders are not deployed and must not be used as unattended production automation yet.
