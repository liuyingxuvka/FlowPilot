## Context

FlowPilot already has a material artifact-map facade and one child policy module
for entry construction. The latest diagnostic still reports the facade as too
large because packet/result envelope indexing and ordinary non-sealed file
scanning live beside the public facade functions.

The repository also contains parallel peer-agent work for repair dossier
context and active child lineage. That work is user-required and must be
preserved. This change may verify those surfaces, but it must not rewrite or
rollback them.

## Goals / Non-Goals

**Goals:**

- Reduce `flowpilot_material_artifact_map.py` below the current public-facade
  split threshold while keeping existing imports and public functions stable.
- Derive child ownership from the existing material artifact-map FlowGuard
  model: packet/result envelope indexing, ordinary work-material scanning, and
  public facade/document writing.
- Preserve exact material policy semantics: index-only map, sealed body text
  exclusion, runtime-open requirement for sealed bodies, and ordinary
  non-sealed file readability.
- Produce current source validation, FlowGuard validation, model-test-code
  diagnostics, topology, install sync, and local git evidence.

**Non-Goals:**

- No new material permission subsystem.
- No new public packet/result schema.
- No compatibility alias or old-shape fallback.
- No rollback or modification of unrelated peer-agent work.
- No claim that the novel-writing task itself is complete; that remains a
  separate product-quality audit.

## Decisions

1. Keep `flowpilot_material_artifact_map.py` as the public facade.

   Existing callers import this module directly. The split moves internal
   helpers out, not public API names.

2. Add focused child modules instead of broad refactors.

   `flowpilot_material_artifact_map_packets.py` owns packet/result envelope
   index entries. `flowpilot_material_artifact_map_ordinary.py` owns ordinary
   non-sealed work-material scanning. `flowpilot_material_artifact_map_entries`
   remains the entry-policy helper.

3. Treat repair dossier and active child lineage work as peer evidence.

   The verification path reruns their focused tests/checks, but commits for
   this change must stage only owned files unless the user explicitly requests
   integration of peer changes.

4. Serialize install sync and audit.

   Installation commands are side-effecting. Sync must finish before audit and
   installed self-check start.

## Risks / Trade-offs

- [Risk] A split could accidentally change map JSON shape.
  -> Mitigation: run material boundary tests, router material modeling tests,
  and the material artifact-map FlowGuard check.

- [Risk] New child modules could create fresh model-test-code gaps.
  -> Mitigation: update code contracts/test evidence and require
  `full_coverage_ok=true`.

- [Risk] Parallel work could make evidence stale.
  -> Mitigation: record dirty worktree boundaries and rerun verification after
  source, model, card, or test files change.
