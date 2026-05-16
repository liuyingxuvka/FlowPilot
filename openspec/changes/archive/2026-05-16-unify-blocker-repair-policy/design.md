## Context

FlowPilot already materializes router `control_blocker` artifacts for several
hard failures. The live router has three lanes: `control_plane_reissue`,
`pm_repair_decision_required`, and `fatal_protocol_violation`. Reviewer blocks,
startup repair, model-miss triage, material insufficiency, terminal ledger
failures, and self-interrogation record failures also stop progress, but they
are not all described through one shared repair policy that PM and Controller
can read.

The user wants the policy to be explicit and practical:

- the table says the first handler, not a separate "PM required" boolean;
- directly repairable mechanical blockers can go to the responsible role first;
- repeated direct failures escalate to PM;
- PM can recover by repairing, rolling back, adding a node, mutating route,
  quarantining evidence, recording an allowed waiver, or stopping for user
  input;
- no blocker disappears silently, and any recovery must return to a named gate
  or terminal stop.

## Goals / Non-Goals

**Goals:**

- Add a durable `blocker_repair_policy` artifact that Router uses for blocker
  triage and PM/Controller can inspect.
- Preserve fast same-role repair for mechanical control-plane failures while
  preventing infinite retry loops.
- Escalate exhausted direct retries, unknown blocker families, and semantic
  blockers to PM.
- Represent PM recovery choices without allowing PM to mark a failed gate as
  passed directly.
- Bring self-interrogation/grill-me record failures into the same blocker
  repair framework.
- Cover the policy in FlowGuard meta/capability checks and runtime tests.

**Non-Goals:**

- Rewriting all existing reviewer, startup, and material repair flows in one
  pass.
- Replacing existing `pm.review_repair`, `pm.model_miss_triage`, or startup
  repair contracts.
- Allowing Controller to inspect sealed bodies or make product/route decisions.
- Allowing a waiver for hard-stop conditions such as protocol contamination,
  broken frozen acceptance, or untrusted terminal evidence.

## Decisions

### Policy table, not scattered keyword intent

Introduce a policy table whose rows include:

- `policy_row_id`
- `blocker_family`
- `first_handler`
- `direct_retry_budget`
- `escalate_to`
- `pm_recovery_options`
- `return_policy`
- `hard_stop_conditions`
- `controller_boundary`

Router may still classify messages from concrete runtime errors, but the
classification output must point at a policy row. The blocker artifact stores
the row snapshot so resumes and PM decisions are based on the policy active
when the blocker was created.

### First handler replaces separate PM-required flag

The table does not need a `pm_required` boolean. If `first_handler` is PM, the
first blocker delivery goes to PM. If the first handler is another role, Router
uses the retry budget before escalating to `escalate_to`, normally PM.

### Retry budgets are conservative

Mechanical control-plane failures use a default direct retry budget of `2`
after the original rejected attempt. That gives the responsible role two direct
repair chances and makes the third same-family failure escalate to PM. Semantic,
review, FlowGuard, self-interrogation, terminal, and fatal protocol blockers use
budget `0`.

### PM recovery is route movement, not silent pass

PM may choose a recovery option that routes around the blocked path, but PM must
record the return gate or terminal stop. Allowed options include same-gate
repair, rollback to an earlier gate, supplemental node insertion, repair node
creation, route mutation, evidence quarantine, allowed waiver, protocol
dead-end, and user stop. A blocked gate cannot be marked as passed by PM text
alone.

### Self-interrogation blockers are PM recovery blockers

Missing, malformed, stale, or dirty `self_interrogation_index.json` records are
not mechanical handoff issues. Router should materialize them with a PM first
handler. PM then re-runs/records self-interrogation, turns hard findings into
repair work, records an allowed waiver, or changes route before the original
gate can be retried.

## Risks / Trade-offs

- **Risk: table drift from router behavior** -> Add tests and FlowGuard checks
  that verify known blocker families resolve through the expected first handler,
  retry budget, escalation, and return policy.
- **Risk: PM waives a hard blocker** -> Encode hard-stop conditions in the
  policy row and validate PM repair decisions against them.
- **Risk: retry loop never ends** -> Track attempts by blocker family, event,
  origin gate, and responsible role; escalate when budget is exhausted.
- **Risk: broad refactor conflicts with parallel agents** -> Keep the first
  implementation focused on control-blocker policy metadata, self-interrogation
  materialization, PM card instructions, templates, and focused tests.
- **Risk: old runs lack policy snapshots** -> Treat missing policy snapshot as
  legacy evidence and fall back to the current policy only for new blockers.

## Migration Plan

1. Add the policy template and default policy rows.
2. Update FlowGuard models with retry/escalation/PM-recovery states.
3. Update Router blocker classification to attach policy metadata and attempt
   accounting to new blocker artifacts.
4. Materialize self-interrogation failures as PM-handled control blockers.
5. Update PM/Controller cards to read and follow policy rows.
6. Add focused runtime tests and run OpenSpec validation, FlowGuard checks,
   router tests, and install sync checks.
