# Service packet operations

## Runtime and configuration

Load `state/service_packets/runtime.json` from this repository before any run. It is private local configuration, deliberately excluded from Git. It names the Python interpreter, repository/data roots, sole desktop spool, registered task, Outlook store/folders/bounds, Google document ID, layout/cue files and Camera/Sound templates. Check that those paths exist and that the registered task action agrees with the configured spool/interpreter. Missing configuration is a setup dependency, not permission to discover arbitrary private folders or reuse an unrelated template. No weekly schedule is implied by this file.

For the current installation, the repository is `C:/worktrees/Document-Generator/weekly-service-packet`; retain it while the registered worker references it. Do not launch parallel native adapters outside the registered worker.

## Collect and snapshot

Use `service_packets.scheduled.queue_job(request, desktop_spool)` to submit. Start the configured task using `Start-ScheduledTask -TaskName <configured-name>`. Read the unique result file and call `jobs.accept_result`; stop after a bounded wait. Do not overwrite `dispatch.json` directly. The registered runner, not the preparing agent, calls `jobs.run_job`.

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

## Interpretation and verification

The agent constructs JSON using `model.py`, `idml.py` and `technical.py`; users do not maintain it. The DOCX remains source evidence even when Nathan explicitly corrects it. Store corrected values with correction-source evidence, and change the item's display wording and the corresponding bulletin paragraphs. The builder does not automatically synchronize those independently authored fields.

After building, read the actual IDML story XML and DOCX contents: verify every corrected reading/title against the accepted value in all dependent artifacts, and confirm the original wording remains in the source record. Do not merely inspect `values` in JSON. Review order and music scope separately from mechanical validation. Proof and visual status must remain distinct from generation status.

## Finalization and deployment gates

Only an explicit final-file designation authorizes baseline promotion. Use `finalize_packet`; do not write baseline.json yourself. Finalization captures do not imply all technical finals are supplied.

No recurring workflow is activated yet. Before cutover: verify a complete ordinary three-service run from current connectors, scheduled Google access, user-approved timing, and explicit replacement of the old automation/export schedule. Preserve old settings for rollback. See `desktop-jobs.md` for ownership recovery; never clear a lock based on age.
