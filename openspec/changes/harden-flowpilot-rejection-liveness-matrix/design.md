## Context

FlowPilot already has several focused safeguards for packet/result contracts,
FlowGuard evidence consistency, parent-scope repair, acceptance-item payloads,
terminal replay, blocker repair information flow, and project-control
information flow. The remaining gap is a parent liveness proof across those
surfaces: if an AI output is rejected or blocked, the next continuation must
either carry a meaningful repair delta, wait for a current external/user event,
or enter an explicit blocker, repair, stop, or break-glass path.

The current live run `run-20260614-184920` is the motivating model miss. Its
ledger records the same `open_startup_intake` next action above the configured
repeat threshold, one `control_plane_stuck` decision, and later ordinary
`process_next_action` decisions for the same action/event generation. Existing
abstract information-flow models flag same-work/no-new-information hazards,
but parent mesh projection can still report safe continuation. This change
repairs that parent proof gap.

The repository policy remains current-contract only. This design must not add
legacy aliases, fallback parsing, old-shape normalization, prose guessing, or a
new side-channel repair ledger.

## Goals / Non-Goals

**Goals:**

- Add a parent FlowGuard model for cross-contract rejection/liveness behavior.
- Add a parent TestMesh for malformed AI output and no-delta retry cells.
- Add live-run projection evidence for repeated same-action/no-new-event loops.
- Require precise repair feedback for mechanical and semantic rejection paths.
- Require same-class fake AI and historical replay evidence for rejected output
  followed by same-payload or same-action continuation.
- Bind the new obligations to runtime code contracts and tests in model-test
  alignment and topology.
- Front-load broad malformed-output case authoring before the final validation
  sweep so missing-field, missing-body, wrong-owner, wrong-id, wrong-enum,
  prose-only, contradictory-pass, stale-evidence, same-payload, and same-action
  retry cases are present before failures are triaged.

**Non-Goals:**

- Do not reopen completed parent repair inheritance or FlowGuard evidence-chain
  changes except where the parent matrix consumes their evidence.
- Do not create a new packet kind, role, repair ledger, or compatibility path.
- Do not claim prepared fake AI payloads prove all live AI semantic failures.
- Do not complete, mutate, or manually advance the unrelated active
  `.flowpilot/current.json` run.
- Do not weaken existing `role_dispatch` behavior; only constrain repeated
  dispatch or user-required actions when no current event or interactive wait
  exists.

## Decisions

### Add a parent rejection/liveness model instead of more isolated regressions

The parent model owns the invariant family:

- rejected output has actionable feedback;
- post-rejection continuation has a semantic delta or current event;
- repeated same action above the threshold is absorbed into a stable blocker,
  repair, stop, user-required wait, or break-glass disposition;
- parent mesh cannot call the live projection green while those conditions are
  unresolved.

Alternative rejected: add only point tests for the latest ledger. That would
catch the observed run but not the same class across packet, FlowGuard,
Reviewer, PM, startup, route, and terminal surfaces.

### Derive finite cells from current contracts

The matrix should use contract-derived payload cells where practical: required
field missing, body/path/hash missing, wrong enum, stale or foreign subject,
intent-field contradiction, prose-only critical content, empty arrays, missing
repair guidance, and no semantic delta after rejection.

Routine confidence should prefer broad cell authoring first and convergence
afterward: add the malformed cells across every practical current contract
family, then run the validation sweep and repair the runtime/model gaps the
sweep exposes. This avoids optimizing the first few cells while leaving
same-class packet/result/report families unmodeled.

Alternative rejected: static hand-picked fake AI fixtures only. They are useful
as historical holdouts, but they do not protect newly added contract families.

### Preserve owner boundaries

Runtime/router owns mechanical rejection, current run identity, packet/result
ids, body/path/hash presence, command/event support, and repeat threshold
absorption. FlowGuard owns substantive state/process/liveness review. Reviewer
owns human quality and sufficiency. TestMesh owns validation hierarchy and
evidence freshness.

Alternative rejected: make FlowGuard or Reviewer compensate for missing
runtime fields. That would hide the mechanical contract break and invite
prose-only recovery.

### Treat stuck detection and stuck absorption separately

The lifecycle guard already can detect a `control_plane_stuck` state. The new
obligation is absorption: after stuck is detected for the same action key and
observed event count, a later refresh must not return to ordinary
`process_next_action` unless a new event, a changed action, a current
interactive/user-required wait, or an explicit blocker/repair/stop disposition
exists.

Alternative rejected: only lower thresholds or count retries differently. That
does not fix the state-machine bug where a detected stuck state can be lost.

### Scope routine and release confidence explicitly

Routine validation should run focused model checks, unit tests, fake AI replay,
historical replay, model-test alignment, topology, install checks, and local
sync checks that are practical in this repository. Release-only suites may
remain visible as deferred only if this change does not claim release
readiness.

## Risks / Trade-offs

- More matrix cells can make validation too broad. Mitigation: split the
  parent TestMesh into contract-derived child suites and keep release-only rows
  visible instead of forcing every slow suite into routine confidence.
- Some repeated user-required actions are legitimate waits. Mitigation: require
  a current interactive/user event boundary or explicit user-required wait
  evidence; otherwise the repeated action is a loop risk.
- Fake AI payload chaos can be overclaimed. Mitigation: keep fake AI rows
  classified as control-flow and contract-boundary evidence, not live AI
  semantic quality.
- Parent mesh can become stale after child model edits. Mitigation: rerun
  model mesh, model-test alignment, topology, and development-process
  freshness checks after model/test/runtime changes.

## Migration Plan

1. Add OpenSpec requirements and task list for the parent matrix.
2. Add the focused FlowGuard model and runner for rejection/liveness behavior.
3. Add the parent TestMesh and broad contract-derived required cell registry.
4. Add fake AI, historical replay, and live-run replay/projection tests for the
   malformed-output and repeated-action matrix.
5. Fix runtime/model mesh behavior exposed by failing new evidence.
6. Bind obligations into model-test alignment and synthetic coverage.
7. Run targeted and adjacent validation, rebuild/check topology, run install
   checks, and sync the local installed skill if source changes require it.
8. Record FlowGuard adoption and KB postflight evidence.

Rollback is ordinary git revert of this change. No runtime data migration is
intended; malformed or old-shape in-flight outputs must be rejected and
reissued under the current contract.

## Open Questions

None for implementation. If validation shows a release-only suite is required
for full confidence, this change may finish with scoped routine confidence and
an explicit release-evidence gap rather than lowering the completion standard.
