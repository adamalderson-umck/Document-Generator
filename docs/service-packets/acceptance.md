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

## Native replay checkpoint

The user authorized a safe native test with both programs available. Initial PowerShell Core Marshal lookup was incompatible; explicit Windows PowerShell 5.1 successfully attached to Word. InDesign active-object lookup was unavailable; its registered `InDesign.Application.2026` COM activation reached the running application (version 21.6.0.57). Both reported zero open documents before composition.

- Added manual proof scripts and a Python adapter contract with busy/failure/stale-result/visual-review tests. These are not a scheduled worker or a full deadline/recovery implementation.
- `rev-001` native exports exposed technical-sheet tab collisions and vertically centered continuation pages. Regression tests were added before correcting the technical renderer.
- `rev-002` contains the corrected editable files. Bulletin: four pages, zero overset, zero missing fonts and zero bad links. Camera: two pages. Sound: one page.
- Inspected all seven rendered pages. Final bulletin page rasters are byte-identical to the initially inspected proof. Revised technical proofs have readable separators and top-aligned continuation, repeated table headers and no observed clipping or split rows. Cue review markers account for extra Camera row height.
- Busy-application smoke tests created only task-owned temporary blank documents. Both native adapters returned `pending / user_documents_open`, produced no busy-test PDF, and left the guard documents open for their owning test to close. No user document was closed or saved.
- Both applications reported zero open documents after normal export. No automatic PDF opening was requested. Foreground focus was not instrumented; background noninterference remains unverified pending user observation and a stronger focus test. Continue user-initiated proofing only.
- Content is still a review draft: inherited dated copy, all unconfirmed cues, and Nathan/music structural disagreements remain findings. Layout inspection does not certify those fields.

Next: confirm focus behavior and source/cue inputs, then proceed to the three-service milestone. No schedule has been enabled or replaced.

## Early-service sources received

The user supplied `Feast of Creation 830am.docx` and `Feast of Creation 930am.docx`. Both were copied read-only into the local acceptance fixture directory and hash-verified, with provenance in `early-orders-manifest.json`. Their headers confirm September 6, 2026 and their respective times. No tables occur in either document.

- 8:30 includes its own opening prayer and Communion sequence, no choir items, and Trinity Chimes before Postlude. Preserve this closing order rather than copying the main service.
- 9:30 orders two opening songs, one song after the opening prayer, and a closing song after Communion. It does not contain the traditional prelude/offertory sequence.
- A fresh read-only Google snapshot was saved as `google-music-snapshot.json`. September 6 section: `A Time`; `Everything's In Your Hands`; `So Will I (100 Billion X)` with catalog identifier 7084123; and the compound `Build My Life / Nothing I Hold Onto`. Preserve list order when matching the four song slots, retain the medley as one slot, and record this mapping as agent interpretation of the two sources.
- Google planning scripture lists Genesis 2.4–25, while Nathan's actual orders list Genesis 1.1–2.3. Nathan remains authoritative; retain the disagreement as a review finding.
- The user confirmed neither application stole focus during the manual native test. This is observed success for that test, not unattended runtime certification.

Remaining replay dependency: the checked output/template/scratch folders contain no separately identified finalized August 30 IDML/INDD. The original labeled template contains August 30 copy but has not been explicitly designated as a finalized prior-week baseline. Ask the user to designate it for this historical acceptance replay or supply the finalized August 30 file. Do not silently substitute the September 6 final as its own previous-week baseline.

Routine Camera/Sound cue assignments also remain unconfirmed; the user supplied files without answering that earlier convention question. Continue visible review markers until authorization is supplied.

## Three-service first replay

The user designated the original template with August 30 information as the baseline for this historical test. Its hash and designation are saved locally. All three September 6 bulletins independently use that template; no production baseline pointer was changed.

Five editable drafts were generated in `outputs/2026-09-06/rev-001/`. Native proofs are in `qa/native-001/`. All bulletins have four pages, zero overset, zero missing fonts and zero bad links. Camera and Sound each have two proof pages. All 16 pages were visually accounted for; identical inherited pages were verified through raster hashes. Unrelated IDML package members match the baseline byte-for-byte in all three drafts.

This is not yet three-service layout acceptance. Visual review found missing thematic headings/inconsistent hymn and reading presentation, a Communion panel boundary needing refinement, and split Sound operator instructions. Those findings are saved in `visual-review.json`. Do not overwrite this revision while fixing them.

Fresh music review found explicit organist scope: only Communion/postlude selections apply to 8:30; solo prelude/offertory selections are not established. Main prayer response is in Nathan's order but declared absent in the music email; preserve and flag that disagreement. Unconfirmed production cues remain visible. Source selection currently includes agent-prepared mappings; the reusable Google adapter and further automated acceptance tests remain to be implemented.

## User corrections: headings and cue defaults

The user explicitly approved existing Camera/Sound template assignments as standing defaults, with exceptions flagged. The maintained cue configuration now records those defaults by semantic cue key. A regression test verifies routine assignment and exception override behavior.

September 6 `rev-002` contains three explicit `OOW Heading` paragraphs in each bulletin (verified in packaged XML). Both technical sheets use routine template cues; only solo introit, solo offertory and disputed choral response remain flagged. Their four proof pages were inspected; the pre-existing Sound instruction-block split remains a separate layout finding.

InDesign had a document open during this run. All three revised bulletin proof operations correctly deferred without touching it. Their new heading layout is therefore structurally verified but not yet visually proofed. Prior revisions remain unchanged. The routine cue mapping is authorized; it does not authorize automatic organ/choir assignments to changed performers.

## September 19 policy clarification and continuity replay

The user explicitly assigned text fit, overset and panel breaks to human cleanup. These findings must be reported, but do not block editable draft delivery or trigger automatic shrinking. This supersedes earlier layout-acceptance gates in this log and the implementation plan. Native proof failure remains distinct from a successful proof with cleanup notes.

The existing finalized September 6 main IDML was reused for September 13, a combined 10:00 service. The existing cleaned September 13 IDML/PDF supplied the comparison reference; no new cleanup was requested from the user. No production baseline pointer was promoted.

- Comparison exposed a renderer defect: the standing `Text Benediction` closing paragraph lived inside the replaced worship story and was dropped. A failing regression test reproduced it, then configured trailing-paragraph preservation fixed it without retaining old worship entries. The paragraph's original character formatting and overrides are preserved.
- New outputs are in `outputs/2026-09-13/rev-003/`. Only the service-heading and worship-order story members differ from the frozen baseline; every other ZIP member is byte-identical.
- Native proofs: bulletin four pages, Camera one page, Sound one page. Bulletin has zero overset, bad fonts or bad links. All six rendered pages were inspected; closing text is visible and technical rows and operator instructions fit. Only the two band items need cue review.
- Nathan's source explicitly says Matthew 18.21-35; the cleaned reference says 18.21-33. The draft follows Nathan and records the difference. Prayer response, postlude and Trinity Chimes in the cleaned reference are absent from Nathan's supplied order; these are content-reconciliation findings, not layout failures. Some additional reference credits/performer labels are also absent from the interpreted source packet.
- Inherited calendar, leaders, flowers and announcements deliberately remain the September 6 baseline copy for human updating. The reference's September 13 updates were not silently treated as input sources.
- Full suite: 68 passed, 1 skipped. Prior drafts and reference files remain untouched.

This verifies the manual main-service continuity replay, not the complete finalization API, atomic baseline promotion, collection worker or scheduled execution. Those implementation tasks remain outstanding.
