# Service packet operations

## Runtime and configuration

Load `state/service_packets/runtime.json` from this repository before any run. It is private local configuration, deliberately excluded from Git. It names the Python interpreter, repository/data roots, sole desktop spool, registered task, Outlook store/folders/bounds, Google document ID, layout/cue files and Camera/Sound templates. Check that those paths exist and that the registered task action agrees with the configured spool/interpreter. Missing configuration is a setup dependency, not permission to discover arbitrary private folders or reuse an unrelated template. No weekly schedule is implied by this file.

The operational repository and data root are `C:/Coding Projects/Document-Generator` on local `main`. The old worktree is retained for its local files only; do not use it for weekly preparation. The registered worker uses a protected deployed copy of its desktop adapter and the main checkout's configured spool. Do not launch parallel native adapters outside that worker.

## Collect and snapshot

Use `service_packets.scheduled.queue_job(request, desktop_spool)` to submit. Start the configured task once using the native Task Scheduler `RegisteredTask.Run` call documented in `desktop-jobs.md`; do not use the ScheduledTasks CIM cmdlets or invoke the worker directly. Read the unique result file and call `jobs.accept_result`; stop after a bounded wait. Do not overwrite `dispatch.json` directly. The registered runner, not the preparing agent, calls `jobs.run_job`.

For `collect_outlook`, write an immutable JSON input containing the configured Outlook fields plus the target `service_date`. For proof/export, copy the selected saved document into the spool as an immutable input. Every request has a unique ID, allowlisted operation, absolute input/output/result paths in the spool, SHA-256 input hash, and an aware UTC deadline. Desktop jobs run sequentially. Busy/unresolved ownership does not prevent independent local generation from already available sources; mark source freshness if collection could not run.

Read `service_packets.collection.select_candidates` and `sources.freeze_sources/read_docx`. Candidate selection preserves all relevant revisions; it does not choose the authoritative one. A message without an attachment can contain the decisive correction. Retain selected and rejected candidates and explain supersession in a local selection record.

Message records must become file-backed candidates before freezing. Example using already saved files:

```python
run = freeze_sources(data_root, sunday, [
    {'id': 'main-order', 'kind': 'nathan_docx', 'scope': ['main'],
     'path': saved_order_path},
    {'id': 'main-correction', 'kind': 'email_snapshot', 'scope': ['main'],
     'path': saved_full_message_json},
])
# source-manifest.json paths are relative to `run`.
# Resolve each as run / entry['path'] when constructing packet sources.
```

Save Google connector content locally with document/revision/tab identity and retrieval time. Select the target year/date section through the next heading and preserve exact ranges as evidence. A successful interactive read does not verify scheduled connector access.

Within a date, select the intended service subsection: morning worship, Charge Conference, and other events are distinct. Never merge them. Match explicit role labels such as Opening Hymn or Offertory to the corresponding slots in Nathan's order. For an unlabeled song list, use list order only when the song count and ordered song slots make the relationship unambiguous; otherwise flag uncertain placement. A medley stays one selection. Retain performers and credits, remove catalog numbers only as metadata, and do not silently normalize an unfamiliar title. An empty section means not supplied, not explicitly no music. An explicit "None" applies only to its named slot. Distinguish supplied, not_supplied, explicitly_absent and unresolved values. Google scripture is supporting context and cannot override Nathan's selected reading. Modern music applies to a combined main service only with explicit applicability evidence.

## Standing music authority

Frank's labeled response instructions control response presence and placement. Prayer responses follow the pastoral prayer and Lord's Prayer; benediction responses follow the benediction. Explicit None omits the response. Nathan need not list the response separately. This user-authorized exception applies consistently to bulletin, Camera, Sound and Proclaim drafts. Preserve the original order and link each response to Nathan's anchor item plus Frank's email. Missing/ambiguous anchors still require review.

Spell-check Dawn's composers and arrangers against authoritative work/score/publisher references, restoring supported diacritics. Retain original spelling and the verified display name with citation. Do not guess an accent, expanded name or composer identity; flag uncertain matches. Camera/Sound element cells stay designation/title only; verified credits belong in bulletin and Proclaim details.

## Modern worship recording artist credits

For the 9:30 bulletin, research a recording-artist display credit for every selected song. Prefer the specific version identified by the Google Doc's recording links or arrangement details. Verify official artist/label/release information. Without version evidence, a clearly supported commonly associated recording artist may be used, with the basis recorded; flag ambiguous song identities or competing versions rather than guessing or implying the team's arrangement is known. Do not equate songwriter, original recording artist, local performer and recording artist.

Keep the source song text, recording-artist credit, songwriter/composer metadata, supporting URL, retrieval date and rationale separate. Preserve medleys and research their components individually. Display the supported recording artist in the existing composer-slot position in the modern bulletin only; retain an unresolved finding when no reliable match is available. Read back the generated story to check each artist remains paired with the right song. This enrichment does not authorize changing the order or music selection, nor adding composer/artist detail to the concise Camera/Sound cells.

Apply credits when generating the 9:30 draft, not by synchronizing or overwriting files after the user's manual finishing edits. This enrichment runs during source preparation; the staged builder controls when each bulletin is produced.

## Interpretation and verification

The agent constructs JSON using `model.py`, `idml.py` and `technical.py`; users do not maintain it. The DOCX remains source evidence even when Nathan explicitly corrects it. Store corrected values with correction-source evidence, and change the item's display wording and the corresponding bulletin paragraphs. The builder does not automatically synchronize those independently authored fields.

After building, read the actual IDML story XML and DOCX contents: verify every corrected reading/title against the accepted value in all dependent artifacts, and confirm the original wording remains in the source record. Do not merely inspect `values` in JSON. Review order and music scope separately from mechanical validation. Proof and visual status must remain distinct from generation status.

## Two-stage build API

`build_packet(packet, data_root, layout, cues, templates, phase="main")` is the default. Retain all three orders in the packet for source review, but generate only the main bulletin plus Camera, Sound and Proclaim. Main uses last Sunday's explicitly finalized main baseline. A missing baseline does not prevent the three DOCX drafts. Missing orders never establish a combined service.

After the user updates the common stories and explicitly designates the saved main final, use the finalization skill. Copy the returned `baseline` into an independent packet copy, then call `build_packet(..., phase="early")`. This requires a finalized main baseline with exactly the packet date; old-date exception evidence cannot bypass it. It generates only the available early/modern bulletins, each from the same frozen baseline, preserving all other IDML members. Do not run this stage for a combined service. Do not reuse phase-one packet.baseline, which is deliberately frozen to the previous week.

Both phases maintain the same weekly folder, `outputs/YYYY-MM-DD/`. The six stable filenames are `main-bulletin.idml`, `early_traditional-bulletin.idml`, `modern-bulletin.idml`, `main-cameras.docx`, `main-sound.docx`, and `main-proclaim.docx`. Main generates four; early generates two. Do not create revision folders or copy completed handoffs into additional delivery folders.

The builder stages rendering in temporary storage and replaces only generator-owned files whose bytes still match their last generated hash. Edited or unrecognized existing files are preserved individually and reported as `manual_edits_preserved`; corrections overlapping those edits require reconciliation in the existing document. An unsuccessful replacement retains the previous usable file and reports it as stale. A file that is open/locked must remain untouched. Main and early metadata have separate manifests under `state/service_packets/builds/YYYY-MM-DD/`; use the returned `manifest_path` and `review_path`, not a hardcoded revision path. Temporary rendering/baseline copies are discarded; keep only current proof results and do not deliver QA snapshots as additional documents. Existing historical folders and untracked files remain in place until separately reconciled.

A later final main can serve next week, but it cannot replace a different Sunday's same-week baseline for an early build. Final captures protect user-designated edits and source evidence; they are not extra weekly handoffs.

### Proclaim enrichment contract

Main items carry `proclaim`: a nonempty list of `{label, text, evidence}` blocks. Each evidence reference must resolve within main-service scope. Place all supplied lyrics, verse restrictions, performers, verified composer/arranger credits, publishing information, prayers/responses and slide instructions with their item. Use `proclaim_notes` for sourced review notes and missing asset references. The reusable renderer generates the full ordered internal DOCX and flags missing enrichment rather than silently claiming completeness. Keep source spelling, accepted correction and supporting authority distinct. No page-count optimization is required.

## Finalization and deployment gates

Only an explicit final-file designation authorizes baseline promotion. Use `finalize_packet`; do not write baseline.json yourself. Finalization captures do not imply all technical finals are supplied.

```python
designation = {
    'path': exact_user_designated_saved_file,
    'date': target_sunday_iso,
    'service': 'main',
    'user_designation': actual_user_authorization,
    'technical': supplied_final_docx_paths,  # e.g. {'cameras': path}; omit missing files
}
# Saved IDML:
record = finalize_packet(data_root, designation)
# Saved INDD, after a matching registered export_final_idml worker request/result:
record = finalize_worker_export(data_root, designation, request, result)
```

For INDD, the request input is a saved-file snapshot inside the sole spool; designation.path remains the original user-designated INDD. `finalize_worker_export` validates the nested native result and original hash, then passes the exported IDML to finalization with original-source provenance. The older direct adapter's `format`/`sha256` envelope is not the registered worker's `operation`/`input_hash` envelope; never connect them by guessing field names. Pending export means no promotion. Missing resources prevent native promotion; fit findings do not. After promotion, verify baseline.json references the returned captured path/hash/service/date. Early capture leaves its previous bytes unchanged.

No recurring workflow is activated yet. Before cutover: verify a complete ordinary three-service run from current connectors, scheduled Google access, user-approved timing, and explicit replacement of the old automation/export schedule. Preserve old settings for rollback. See `desktop-jobs.md` for ownership recovery; never clear a lock based on age.

## Early-service personnel handoff

Personnel are not assumed common across services. Keep the inherited main-service story unchanged in early drafts, but explicitly flag welcome-team, worship-leader and technical-team details for the user to replace manually before publication. Do not claim service personnel are verified merely because common IDML members were preserved. This is the user-approved manual finishing boundary.

## Broadcast boundary

The Camera sheet stops before Exit Music because the broadcast ends there. Keep Benediction Response, Postlude and Trinity Chimes when present in the canonical order. Sound and Proclaim retain Exit Music. Identify the exit selection with kind `exit_music` (the exact Nathan label `Exit Music` is also recognized). Do not drop Benediction Response to reproduce the September 20 canonical Camera oversight, which the user explicitly confirmed.

## Standing traditional music and bulletin terminology

User-confirmed standing rules: Dawn's organ prelude and postlude apply to both early_traditional (8:30) and main, unless an explicit service-specific correction supersedes them. Scope the organ source to both services and retain the standing applicability authority plus original email evidence. Use the verified composer spelling in both. The early offertory uses the organ Exit Music selection; New Spirit remains main only. Preserve Nathan's original evidence, but omit Trinity Chimes from the 8:30 bulletin under this explicit standing exception; do not omit it from main.

The maintained layout configuration supplies bulletin-only labels: Praying with Our Community; Anthem; Choral Response (for the benediction response); Call to Worship (without the parenthetical reference). Do not rewrite source_wording or remove full prayers, references, response placement or verse details from Proclaim. Source interpretation must populate both services' music before building; the renderer never borrows another service's music by guessing from text.

## Bulletin music-title quotation marks

User instruction, confirmed in the finished September 27, 2026 main bulletin: wrap every displayed musical selection title in typographic double quotation marks (“Title”), including hymns, modern songs, choir pieces, and instrumental prelude/offertory/postlude/exit selections. Apply this to all service bulletins during preparation. Quote only the title field, not the worship-order designation, Scripture reference, hymnal/catalog number, composer, arranger, or recording-artist credit. Preserve internal punctuation and do not double-wrap an already quoted title. Keep original source wording unchanged in the source evidence. Do not rewrite a user-finished bulletin to apply this rule; preserve its manual edits.

## Bulletin sermon speaker

User instruction, October 4, 2026: show the sermon speaker in the rightmost tab field on the same line as Sermon, leaving the middle field empty: `Sermon\t\tRev. Nathan Howe`. Apply this to all service bulletins during preparation. Rev. Nathan Howe is the usual speaker under this standing instruction; use the service-specific speaker when a source or explicit user correction identifies someone else, and flag conflicting or ambiguous assignments for review. Populate both the sermon item's `bulletin_text` and its corresponding `bulletin_paragraphs` entry. Preserve original `source_wording` and evidence, and retain concise Camera/Sound `technical_wording` without the speaker. Read back the generated story to verify both tabs and the speaker field. Do not rewrite a user-finished bulletin or overwrite later manual edits to apply this rule.

## Sound rows with an unchanged scene

User instruction, October 4, 2026: successive worship items using the same confirmed Sound scene may be combined into a single Sound row. Show the scene once and retain every item's concise worship-element wording on separate lines in canonical order. Combine only adjacent items; an intervening different or unresolved scene ends the group. Keep unknown cues and cue exceptions visible, and preserve any item-specific operational instructions. This is Sound-sheet presentation only: retain distinct canonical packet items and their evidence, and do not group Camera or Proclaim entries under this rule. The technical renderer automatically combines adjacent items only when their confirmed, nonblank Sound instructions match exactly. It retains each worship element on a separate line and preserves every item ID in the artifact record; Camera rows remain individual. Do not overwrite edited handoffs.
