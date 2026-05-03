# Defect Governance FlowGuard Risk Intent

## Scope

This model protects FlowPilot's run-level defect and evidence governance. It is
not a product-specific model. It covers defects discovered by PM, reviewer,
FlowGuard officers, workers, or the main executor while a formal FlowPilot run
is active.

## Failure Modes

- A blocker is mentioned in a reviewer or officer report but never enters a
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

- Every blocking review, officer, or PM finding creates a defect event before
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

## Residual Blindspots

This model does not prove that a human reviewer made a good aesthetic judgement
or that a test fixture perfectly represents a real project. It only proves that
the governance state cannot silently skip required registration, triage,
recheck, evidence classification, and pause snapshot steps.
