## Context

FlowPilot already has a route-mutation cleanup helper, `_supersede_repair_open_blockers_for_route_mutation`, and an existing historical status, `superseded_by_route_mutation`. The current helper closes repair-open blockers when their repair packet is directly affected by the mutation, or when an obsolete same-family blocker can be proven stale through affected packet family keys.

The observed gap is narrower: a later route mutation can advance the route version while older `repair_packet_open` blockers from earlier route versions remain open in raw `active_blockers`. Those rows are no longer current work once the route version has moved on, but they still look open to a human ledger audit.

## Goals / Non-Goals

**Goals:**

- On route mutation commit, close stale `repair_packet_open` blockers whose numeric `route_version` is older than the mutation's `new_route_version`.
- Use the existing `superseded_by_route_mutation` lifecycle and existing metadata fields.
- Keep the cleanup idempotent and local to route-mutation commit paths.
- Prove the change through focused runtime tests, FlowGuard information-flow checks, model-test alignment, topology refresh, and install sync.

**Non-Goals:**

- No new persistent fields.
- No broad semantic same-problem classifier.
- No PM/reviewer prompt redesign for this small fix.
- No mutation during final-preflight or status reads.
- No compatibility fallback for missing or nonnumeric route versions.

## Decisions

1. Route mutation commit owns stale repair-open retirement.

   The helper that already handles affected repair packets will also retire stale repair-open blockers whose `route_version` is numerically lower than the mutation's `new_route_version`. This keeps the lifecycle transition at the point where the route actually changes, not in read-only reporting code.

   Alternative rejected: hide the rows only in status/final-preflight. That leaves raw ledger state misleading and makes future audits depend on every reader reimplementing the same filter.

2. Numeric old route version is the proof boundary.

   A blocker is stale for this new rule only when it is `repair_packet_open` and its `route_version` can be parsed as an integer lower than `new_route_version`. Current-version blockers and blockers with missing/nonnumeric versions stay untouched.

   Alternative rejected: retire every unrelated repair-open blocker on mutation. That is too broad when the ledger cannot prove the blocker belongs to an older route.

3. Existing historical status and event are reused.

   The runtime will call `_mark_repair_open_blocker_superseded_by_route_mutation` so the event stream and metadata shape stay consistent with existing route-mutation supersession.

   Alternative rejected: add a new status such as `stale_after_route_version_advance`. That would create field/status maintenance debt without adding a materially different lifecycle state.

## Risks / Trade-offs

- Older ledgers without numeric `route_version` may still contain open-looking rows. Mitigation: this is intentional; the rule only acts when stale route ownership is provable.
- This does not clean already-written historical runs unless another route mutation is processed. Mitigation: the requested repair is for the FlowPilot software path, not ProjectRadar run-data migration.
- A current route mutation may retire old blockers from several prior route versions at once. Mitigation: once a new route version is active, prior-route repair packets are no longer current execution authority, and the rows remain preserved as historical evidence.
