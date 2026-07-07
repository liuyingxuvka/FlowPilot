## Context

FlowPilot already has the required authority surfaces:

- current run ledger;
- lifecycle guard;
- foreground duty;
- final return preflight;
- final closure record;
- route/node/blocker ledgers.

The observed bug is that some derived surfaces do not consistently consume that
authority. A user or future agent can see `complete` in one file while another
surface still shows null, unknown, awaiting, or a cleared blocker as current.

## Decisions

1. Projection is a derived view, not a second authority.

   `console/status.json`, ledger `status_projection`, and display summaries
   derive from the current ledger and guard/preflight functions. They must not
   search other runs, infer from historical artifacts, or normalize legacy
   fields.

2. Current blockers are computed, not stored as a new durable field.

   The ledger may retain historical rows under the historical name
   `active_blockers`, but public current projections and role-memory current
   rows must filter through the existing current-effective blocker predicate.
   Historical rows may remain available for audit context only.

3. Closing a node must close its node-closure projection.

   When PM disposition accepts, blocks, stops, or replaces a node, the existing
   node closure row for that node must leave `awaiting_pm_disposition` and
   record the PM disposition id. This is a convergence side effect of the
   existing PM disposition path, not a new state family.

4. Repair dossiers must stop presenting noncurrent blockers as active.

   A dossier may remain as history for lineage, but its current active blocker
   pointer must be empty/noncurrent once the blocker is cleared, retired,
   superseded, or its route node is noncurrent.

5. Cartesian coverage is finite and explicit.

   The model must enumerate closure state, blocker state, node-closure state,
   repair-dossier state, and projection surface combinations. Each cell must be
   accepted as a current projection, classified as history-only, or rejected as a
   control-plane projection miss.

## Risks / Trade-offs

- [Risk] Filtering current blockers could hide useful repair history.
  -> Mitigation: keep history in ledger and historical context, but keep public
  current status and role-memory current rows filtered.

- [Risk] Adding projection fields could look like a new status contract.
  -> Mitigation: use derived fields already present in `.flowpilot/current.json`
  and existing final-preflight/closure concepts; do not accept new input fields.

- [Risk] Run-shell save order could write a stale `status_projection`.
  -> Mitigation: refresh lifecycle guard first, refresh projection before the
  ledger write, then materialize artifacts from the same in-memory ledger.
