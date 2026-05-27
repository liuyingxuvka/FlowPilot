## Context

FlowPilot already has the key authority surfaces needed for safe reuse:
packet runtime envelopes and open receipts, PM package result dispositions,
PM formal gate packages, reviewer material sufficiency reports, route memory,
PM suggestion ledgers, self-interrogation records, evidence ledgers, and the
final route-wide ledger. The missing part is a derived index that lets roles
find previously produced material without treating sealed packet/result bodies
as shared files.

The current blocker pattern is visible in material sufficiency: PM can absorb
worker scan results and release a formal package, but the package mostly cites
result envelopes and hashes. A reviewer can mechanically audit packet identity,
but still lacks a stable role-readable material map that names which safe
source refs were reviewed, which items are stale or blocked, and which items
require runtime opening.

## Goals / Non-Goals

**Goals:**

- Add a minimal run-scoped material artifact map as a derived JSON artifact.
- Preserve all sealed packet/result body boundaries; the map never copies
  sealed body text.
- Let PM packets explicitly grant workers access to selected map entries.
- Let reviewer material sufficiency cite concrete PM package/material-map/source
  refs and rely on existing packet-runtime receipts for sealed result-body
  evidence.
- Link the map from route memory and final ledger so later PM decisions can
  find prior materials without using Controller summaries as evidence.

**Non-Goals:**

- No new permission service, database, search UI, or role-to-role mailbox.
- No broad access to sealed worker result bodies.
- No new approval authority; gates still pass or block through existing PM,
  reviewer, runtime, and ledger contracts.
- No requirement that every role inspect every historical artifact.

## Decisions

1. Use a derived JSON map instead of a new authority store.
   - Chosen path: write `.flowpilot/runs/<run-id>/material/material_artifact_map.json`.
   - Rationale: existing packet ledger, role output envelopes, PM packages,
     route memory, and final ledger remain the source of truth.
   - Alternative rejected: a separate access-control service would duplicate
     packet runtime authority and add unnecessary operational surface.

2. Keep map entries metadata-first.
   - Entries carry `entry_id`, `kind`, producer/owner roles, status, authority
     level, source paths, envelope paths, hashes, safe summary, allowed roles,
     and whether runtime open is required.
   - They do not carry sealed packet body text, sealed result body text, or
     Controller-authored evidence.

3. Integrate at existing write points.
   - Material scan packet creation, PM package disposition, material
     sufficiency, research package/result absorption, PM material understanding,
     route-memory refresh, and final-ledger source scans refresh or reference
     the map.
   - This keeps the map current without adding a daemon or watcher.

4. Use packet-declared reads for worker autonomy.
   - PM packets may include `allowed_material_map_entry_ids` in metadata/body
     guidance. Workers can inspect those entries as part of the opened packet
     boundary.
   - Entries requiring runtime open still require packet runtime authority; a
     worker that lacks it reports `needs_pm` instead of ordinary file-reading a
     sealed body.

5. Strengthen reviewer material sufficiency only where needed.
   - Reviewer reports already require `direct_material_sources_checked` and
     `checked_source_paths`. The change makes empty checked paths invalid when
     the report claims a direct source check.
   - PM formal packages provide `material_artifact_map_path`,
     `review_source_entry_ids`, and `reviewable_source_paths` so the reviewer
     has concrete refs without raw worker body leakage.

## Risks / Trade-offs

- Map drift -> Refresh the map only from stable existing artifacts and write
  source artifact hashes/paths into each entry.
- Over-claiming map authority -> Mark map summaries as navigation/index data
  and keep gate authority in PM/reviewer/runtime reports.
- Reviewer false confidence -> Require checked source paths or runtime-open
  receipts for direct source claims.
- Scope creep -> Do not add search UI, permission service, or broad historical
  query features in this change.

## Migration Plan

1. Add the focused map helper and schema constants.
2. Wire existing material/research/PM package writers to refresh or reference
   the map.
3. Update runtime-kit cards/contracts to explain the existing-boundary access
   path.
4. Add a focused FlowGuard model for map states and invariants.
5. Add targeted router/runtime tests and prompt coverage tests.
6. Sync the installed local `flowpilot` skill after source validation.

Rollback is simple: remove references to the map from package/context writers
and leave existing PM package, packet runtime, and reviewer gates unchanged.

## Open Questions

- Whether future UI/search affordances should be built on top of the map is
  intentionally deferred.
- Whether officer model reports need a richer subtype taxonomy can be handled
  after the first material/research/reviewer path is stable.
