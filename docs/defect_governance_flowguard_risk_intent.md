# Defect Governance FlowGuard Risk Intent

## Scope

This model protects FlowPilot's run-level defect and evidence governance. It is
not a product-specific model. It covers defects discovered by PM, reviewer,
FlowGuard operators, workers, or the controller while a formal FlowPilot run
is active.

## Failure Modes

- A blocker is mentioned in a reviewer or FlowGuard operator report but never enters a
  canonical run ledger.
- A route advances because the implementation was patched, even though the same
  class of reviewer has not rechecked the fix.
- Invalid, stale, fixture-only, or superseded evidence is overwritten by newer
  screenshots or reports without recording why the old evidence cannot close a
  gate.
- A terminal completion report is written while defect or evidence ledgers still
  contain unresolved blocker, test-gap, evidence-gap, or route-gap items.
- A controlled pause stops heartbeat work but leaves no readable snapshot of the
  current node, blockers, pending rechecks, automations, agents, and cleanup
  boundary.
- FlowPilot skill/process weaknesses are recorded only at terminal closure, so
  a paused or restarted run loses the lesson.

## Hard Invariants

- Every blocking review, FlowGuard operator, or PM finding creates a defect event before
  route repair or closure can continue.
- PM triage is required before a blocking defect can be assigned, repaired, or
  closed.
- A fixed blocker enters `fixed_pending_recheck`; it cannot become `closed`
  until the matching role class records recheck evidence.
- Evidence may be `valid`, `invalid`, `stale`, or `superseded`, and its source
  kind must distinguish live project evidence from fixture, synthetic,
  historical, and generated concept evidence.
- Terminal completion requires zero open blockers and zero fixed-pending-recheck
  defects.
- Controlled nonterminal pause requires a pause snapshot.

## Recurring Defect-Family Promotion

A single modelable bug can close through the ordinary defect flow after the
observed failure, same-class recheck, and post-repair model check are current.
When the same class appears again, or when a first failure is high risk enough
that a local point fix would overclaim confidence, FlowPilot must promote it to
a FlowGuard defect-family gate.

The known high-level dirty families are currently:

- `worker_self_check_failure`: worker result bodies look complete but miss
  machine-checkable contract fields.
- `pm_repair_atomicity`: PM repair decisions expose follow-up events before
  daemon-visible repair state is committed.
- `producerless_repair_continuation`: a repair waits on stale result flags or
  names an event without a concrete current producer or safe operation replay.
- `status_projection_stale`: user-visible status or route display is generated
  from stale Router facts.
- `ack_false_blocker`: ACK receipt clearance is confused with semantic role
  output completion, or a resolved ACK reappears as a blocker.
- `controlled_stop_reconciliation`: stop/cancel releases one lifecycle surface
  while current pointers, daemon state, heartbeat/manual-resume, or role
  continuation still look active.

Each family needs a model obligation, authority boundary, observed historical
failure, same-class generalized case, historical holdout, and current external
proof. The Risk Evidence Ledger must consume the family gate before any final
full-confidence claim. Progress-only, stale, skipped, model-only, or
internal-only proof is not enough.

## Residual Blindspots

This model does not prove that a human reviewer made a good aesthetic judgement
or that a test fixture perfectly represents a real project. It only proves that
the governance state cannot silently skip required registration, triage,
recheck, evidence classification, and pause snapshot steps.
