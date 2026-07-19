# Model-Miss Review: Parent Segment Route-Memory Authority

## Observed discrepancy

The same-fingerprint `all` tier exposed
`test_parent_backward_non_continue_decision_mutates_route_and_requires_rerun`.
The PM parent-segment decision validated the current route-memory snapshot,
wrote `pm_parent_segment_decision.json`, and then the nested route-mutation
writer mechanically validated route memory a second time.  The second check
correctly saw that the event-local decision write had changed a tracked source
and rejected the mutation as stale.

## Ownership decision

- Runtime freshness remained correct and was not weakened.
- The failure belonged to the route-mutation event transaction: one logical
  PM decision was consuming the same authority twice on opposite sides of an
  event-local write.
- No compatibility reader, refresh fallback, old snapshot acceptance, second
  ledger, or persisted authority field was added.

## Current-contract repair

The event now validates current route-memory authority once, before any
event-local write, and keeps the result in an ephemeral typed authority
object.  The durable PM decision and the staged route-mutation proposal consume
that same object.  Ordinary route-mutation entry still performs its own current
snapshot validation.  A raw mapping cannot impersonate the typed authority.

## Backfeed

- FlowGuard route-mutation activation now models pre-write validation,
  same-authority consumption, and the self-invalidating repeated-validation
  hazard.
- MTA keeps the external owner at `router.record_external_event` and adds the
  parent non-continue success case as current route-mutation evidence.
- The route-mutation tier owns both the repaired positive case and the
  unvalidated-authority negative case.
- Interrupted `all` evidence was invalidated; its remaining live child process
  trees were terminated with descendant-zero confirmation before another
  execution owner may start.
