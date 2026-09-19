---
name: finalize-service-packet
description: Use when the user identifies finished bulletin IDML or INDD files, wants to record final service documents, or designates the main-service baseline for the following week.
---

# Finalize a service packet

Capture explicitly designated finished work without changing originals. A final main-service bulletin may become next week's baseline; early-service finals never replace that pointer.

Read `docs/service-packets/operations.md`, `desktop-jobs.md` in that directory, `state/service_packets/runtime.json`, and `service_packets/finalize.py` before execution.

## Establish the designation

Confirm the exact saved file, Sunday date, service key (`early_traditional`, `modern`, or `main`) and intended scope from the user's request. "Looks good" on a draft, newest modification time, and an earlier historical-test designation do not authorize production promotion. If unclear, ask for the missing designation only. Do not ask the user to redo cleanup when finished files already exist. Do not reverse-parse a manually edited bulletin into technical sheets.

Use the existing cleaned files for historical acceptance in an isolated root. Never let those tests update production state. Record a supplied older-final exception explicitly; do not add exception evidence merely to bypass a stale-baseline check.

## Capture

Build a designation dictionary as shown in operations. `user_designation` records the user's actual authorization, not an agent-invented approval. Include only actually supplied final Camera/Sound paths in `technical`; missing ones remain outstanding and do not by themselves prevent an authorized main promotion.

For a saved IDML, call `finalize_packet(data_root, designation)`. It validates/captures the file and atomically promotes an eligible main baseline. Never write `baseline.json` directly.

For a saved INDD:

1. Check sole-spool ownership. An unresolved timeout blocks all desktop work, regardless of lock age. Do not clear locks, kill applications, create another spool or call the old direct adapter.
2. Snapshot the exact designated saved INDD into the configured spool. Submit `export_final_idml` with `scheduled.queue_job`; start only the registered task. Any open InDesign document, including an unsaved one, defers export. Never close or save the user's document.
3. Preserve the request/result and call `finalize_worker_export(data_root, designation, request, result)`. This checks matching job/input/output hashes, native completion, fonts/links and original INDD identity, then invokes the finalizer while retaining original-file provenance. Do not pass nested native results directly into `finalize_packet` or mistake a PDF export for IDML.

## Verify and report

Read the returned capture and baseline pointer, and verify hashes/files. A capture record states promotion intent; the atomically replaced pointer establishes actual promotion. Native export does not establish editorial or visual approval. Report overset as human cleanup; never silently shrink or remove content.

Report exact captured paths, whether the main pointer changed, missing technical finals and any pending export. Distinguish `queue_job` refusal from a worker's pending result. Ownership recovery remains manual: preserve evidence and request reconciliation, not permission to force-close apps. Do not enable, replace or merge schedules as part of finalization.
