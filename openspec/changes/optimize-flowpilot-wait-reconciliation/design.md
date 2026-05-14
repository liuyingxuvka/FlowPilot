## Context

FlowPilot currently supports direct Router ACKs, active-holder leases, parallel
packet batches, packet/result envelopes, and PM role-work requests. The slow
path is not absence of parallelism; it is stale or coarse waiting after durable
packet evidence already exists. A live run showed one material-scan result
envelope present while the batch counter still said zero results and the status
summary named the wrong waiting role.

The existing control-plane safety model is strict: Controller may relay packet
metadata but must not read sealed bodies, PM owns package-result disposition,
reviewer gates must inspect formal PM packages, and terminal closure must not
hide unresolved advisory work. This design preserves those boundaries while
reducing unnecessary waiting.

## Goals / Non-Goals

**Goals:**

- Reconcile durable packet evidence before the Router emits another wait.
- Track partial batch completion at member level.
- Let the Router continue non-dependent work while pending packets remain open.
- Keep blocking PM/reviewer/material gates blocked until blocking dependencies
  are complete.
- Extend active-holder direct ACK/progress/result handling to material scan,
  research, and PM role-work packets where the Router knows the live holder.
- Make prompt cards and runtime event authority agree.
- Prove the model catches known-bad hazards before runtime changes.

**Non-Goals:**

- No remote GitHub push, release, or pull request.
- No weakening of PM/reviewer authority.
- No Controller access to sealed packet or result bodies.
- No broad route-system rewrite beyond the wait/reconciliation path.
- No hidden migration of unrelated state or cleanup of other agents' work.

## Decisions

### Decision 1: Reconcile first, then choose next action

Before `next_action` chooses a wait, the Router will refresh active packet
state from durable evidence: packet ledger entries, ACK records, result
envelopes, and controller status packets. This keeps the Router from reissuing
a wait that was already satisfied.

Alternative considered: add shorter polling or repeated check-in prompts. That
would make the visible loop busier without fixing the state drift.

### Decision 2: Batch state is packet-member state, not only aggregate flags

Batch records will keep per-packet status, holder role, dependency class,
result envelope path, returned timestamp, and missing-role projections.
Aggregate fields such as `results_returned` become derived or refreshed from
member status.

Alternative considered: keep a single batch-level `worker_scan_results_returned`
flag. That cannot represent A returned while B is still pending, so it repeats
the current stale/coarse wait problem.

### Decision 3: Continuation is dependency-aware

Each packet or PM role-work request is classified as `blocking`, `advisory`, or
`prep-only`, and can list the gate ids it blocks. The Router may select
non-dependent actions while pending work exists, but it cannot cross a gate
whose `blocks_gate_ids` still contains unresolved blocking work.

Alternative considered: allow all continuation while packets are pending. That
would be fast but unsafe because PM/reviewer decisions could be made on partial
evidence.

### Decision 4: Active-holder direct path becomes packet-type agnostic

The same lease rules used for current-node packets will apply to material scan,
research, and PM role-work packets when the Router knows the live holder and
can bind run id, packet id, holder role, and result target. The fallback remains
the existing Controller relay path when no live holder is available.

Alternative considered: keep active-holder only for current-node packets. That
leaves material and research loops on the slower path even though they have the
same safe metadata boundary.

### Decision 5: Prompt changes are contract changes

Prompt cards must not merely suggest speed. They must require dependency class,
join policy, allowed return events, and active-holder behavior. Role cards must
tell workers/officers to use Router-supplied events only.

Alternative considered: rely on runtime validation alone. Runtime validation is
necessary, but prompt/runtime drift is already a known FlowPilot risk and must
be modeled and tested.

### Decision 6: Second-perspective cleanup is alignment, not a new controller

The OpenSpec/FlowGuard pass is used as an independent review lens over the
existing FlowPilot implementation. It may repair stale paths, missing scenarios,
task evidence wording, and equivalence notes, but it does not promote OpenSpec
to the FlowPilot control plane or reopen unrelated runtime slices.

Alternative considered: re-plan the full FlowPilot controller under OpenSpec.
That would mix a verification pass with a control-plane migration and hide the
smaller concrete drift found by the audit.

## Risks / Trade-offs

- Stale result consumed twice -> Mitigation: packet-id keyed reconciliation,
  idempotent counters, repeated-tick model scenarios, and duplicate runtime
  tests.
- Partial result crosses protected gate -> Mitigation: dependency-class fields,
  `blocks_gate_ids`, model invariants, and gate-specific runtime assertions.
- Advisory work disappears -> Mitigation: advisory requests do not block
  ordinary non-dependent work but must be absorbed, canceled, superseded, or
  carried before terminal closure.
- Status leaks sealed content -> Mitigation: status summary can expose only
  ids, roles, timestamps, counts, and progress numbers, never result findings or
  body summaries.
- Prompt promises unsupported behavior -> Mitigation: card coverage and event
  contract models must fail unsupported partial-continuation wording.
- Other agents' edits are overwritten -> Mitigation: inspect `git status`
  before each slice, avoid repo-wide formatters, and keep file sets scoped.

## Migration Plan

1. Create the paper plan and OpenSpec artifacts.
2. Upgrade FlowGuard models and add known-bad hazard coverage.
3. Run model checks and confirm known-bad hazards are visible.
4. Update the intended model path until all required model checks pass.
5. Implement runtime slice 1: wait reconciliation.
6. Run targeted model and router tests.
7. Implement runtime slice 2: partial batch accounting and status summary.
8. Run targeted model, router, and packet tests.
9. Implement runtime slice 3: active-holder expansion.
10. Run targeted router-loop and packet runtime tests.
11. Implement runtime slice 4: dependency-aware continuation.
12. Run decision-liveness, event-contract, and router tests.
13. Update prompt cards, templates, and docs.
14. Run full practical verification and local install sync.
15. Stage and commit local git changes only.

Rollback is local git revert of the commit. No remote publication is part of
this change.

## Open Questions

- Whether to store ready-queue entries durably or derive them from refreshed
  packet state on each Router tick. Default: derive first, persist only if tests
  reveal resume ambiguity.
- Whether material/research batches should immediately relay each returned
  result to PM or wait for the batch join before PM disposition. Default:
  record partial returns immediately, but keep formal PM disposition and
  reviewer gates behind the blocking join.
