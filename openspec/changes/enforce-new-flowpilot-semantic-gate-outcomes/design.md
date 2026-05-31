## Context

The fresh FlowPilot runtime intentionally replaced old Router/card complexity
with a smaller packet lifecycle:

`task -> flowguard_check -> review -> system_validation -> system_closure -> PM disposition`.

That symmetry is useful, but it currently mixes two different meanings:

- "The packet result was mechanically valid and came from the right lease."
- "The role's semantic decision was pass/accept."

The old FlowPilot protocol kept these separate. The Controller/Router validated
mechanics; reviewer and FlowGuard operator responsibilities own semantic
pass/block where requested; system validation and system closure are runtime
ledger outcomes; PM owns repair strategy. The new runtime should restore that
boundary without dispatching Validator or Closure Officer role packets.

## Decisions

### Decision: Add one compact outcome contract instead of old cards

Every packet result can carry a `black_box_flowpilot.packet_outcome.v1` body or
the equivalent fields in a role-specific body:

- `decision`: `pass`, `accept`, `complete`, `block`, `fail`,
  `needs_more_evidence`, `needs_pm`, `waive`, or `stop`.
- `blocking`: boolean, derived when omitted.
- `blocker_class`: `local_artifact`, `evidence_gap`, `validation_failure`,
  `flowguard_failure`, `route_invalidating`, `protocol_error`,
  `stale_evidence`, `needs_user`, or `unknown`.
- `recommended_resolution`: PM-actionable repair recommendation.
- `evidence_refs`: current-run evidence references.

Fake/rehearsal bodies must state an explicit pass/accept/complete outcome.
Plain bodies from reviewer or FlowGuard operator responsibilities that contain
clear block/fail terms are treated as non-pass.

### Decision: Separate outcome records from active blockers

The ledger records all semantic outcomes under `packet_outcomes`. Non-pass
outcomes additionally create `active_blockers`. A blocker names the packet,
subject packet, target result, gate kind, owner role, required recheck role,
repair generation, recommendation, and stale evidence ids.

This makes history inspectable without letting old failed evidence become
passing evidence.

### Decision: PM repair decisions are packets, not side commands

The runtime automatically issues a `pm_repair_decision` packet to PM when a
semantic blocker is active and no current repair decision packet exists. The PM
decision is itself a sealed packet result and may choose:

- `same_node_repair`
- `sender_reissue`
- `collect_more_evidence`
- `rerun_validation`
- `mutate_route`
- `quarantine_evidence`
- `waive_with_authority`
- `stop_for_user`

Router/system code applies only routeable mechanics. PM remains the owner of
repair strategy; reviewer and FlowGuard operator responsibilities do not repair
the artifact themselves.

### Decision: Recheck is mandatory for clearing blockers

A blocker created by a reviewer block is cleared only when the same gate class
gets a newer reviewer pass. A system validation failure is cleared only by
newer current evidence that passes the system validation step. A FlowGuard
failure is cleared only by a newer FlowGuard operator pass. PM repair decisions
can start repair work, mutate route, quarantine evidence, or stop, but they do
not themselves clear the blocker except for an explicitly authorized waiver.

### Decision: Same-node repair remains the default local repair

If the blocked work belongs to a route node and the PM selects
`same_node_repair`, the runtime uses the existing repair-generation path:
stale current evidence, keep the same node active, reissue bounded work, and
require the same downstream checks again. Route mutation remains available only
for structural findings.

## Risks / Trade-offs

- Outcome parsing can over-read free text -> structured JSON has priority; free
  text detection is intentionally conservative and mainly catches direct
  block/fail wording.
- PM repair packets add one more packet in failure cases -> only non-pass cases
  pay that cost; successful paths stay unchanged.
- Waivers can be abused -> waiver clearing requires explicit
  `waive_with_authority` and records the reason/evidence in the blocker.
- Same-node repair might not fit every blocker -> PM can choose route mutation
  or stop when the current node cannot contain the repair.

## Migration Plan

1. Add OpenSpec requirements and tasks for semantic gate outcomes.
2. Add a focused FlowGuard model for pass/block/fail outcome lifecycle.
3. Extend ledger initialization, packet-result application, outcome parsing,
   active blocker recording, PM repair packet issuing, PM repair application,
   and public status projection.
4. Add focused tests for reviewer block, system validation fail, worker
   blocked, PM repair decision issuance/application, same-class recheck, and no
   silent pass.
5. Run OpenSpec validation, FlowGuard project audit, focused model checks,
   targeted pytest, fake rehearsal, install sync/audit/check, and background
   heavier model checks where practical.
6. Stage/commit only scoped files if validation is green and unrelated dirty
   worktree changes remain separate.

Rollback strategy: the change is isolated to the new runtime packet path. If
the new checks fail, keep the OpenSpec change active and do not sync the local
installed skill as upgraded.
