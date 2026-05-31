## Why

FlowPilot can currently produce a complete-looking design route and still stop
before the user has a practical next step, such as a first runnable data pass.
Formal FlowPilot work needs a lightweight guard against this shallow completion:
the process should catch the task-specific "looks done, but is not useful yet"
failure without adding a heavy new planning schema.

## What Changes

- Add a small task-specific shallow-completion trap list to PM route planning using the
  existing product usefulness, low-quality-success, and self-interrogation
  surfaces.
- Require PM route planning to route, merge, waive, or block each current trap instead of
  allowing an all-design route to pass when the user outcome requires an
  executable, runnable, reviewable, or handoff-ready result.
- Require Reviewer active challenge to probe the current trap list from the final user's
  point of view and block existence-only or report-only proof when any current
  trap remains plausible.
- Require terminal closure to replay the final output against the original user
  outcome and block closure when the delivered result still leaves the user's
  obvious next step undefined.
- Add focused FlowGuard/model regression coverage for design-only route pass,
  reviewer downgrade to nonblocking, and ledger-only closure pass.
- Preserve FlowPilot's lightweight posture by extending existing cards and
  focused model checks instead of adding a broad new runtime schema or field
  matrix.

## Capabilities

### New Capabilities

- `flowpilot-shallow-completion-guard`: Lightweight PM, Reviewer, and Closure
  behavior that prevents shallow completion traps from passing formal FlowPilot
  gates.

### Modified Capabilities

- `formal-gate-review-standards`: Reviewer gate behavior must block current
  shallow-completion traps instead of treating them as nonblocking improvements.
- `flowpilot-closure-kernel`: Terminal closure must preserve semantic final-user
  outcome replay and must not let clean lifecycle evidence substitute for user
  usefulness.
- `self-interrogation-disposition`: PM self-interrogation disposition must keep
  task-specific shallow-completion traps visible through protected gates.

## Impact

- Affected prompt cards: PM route skeleton, Reviewer node-completion review,
  PM closure, and closely related PM product/contract cards if needed.
- Affected models/checks: planning quality, reviewer active challenge, and any
  focused closure or terminal replay check that already owns this boundary.
- Affected tests: planning-quality, reviewer active-challenge, card instruction
  coverage, and targeted install/card validation.
- Affected install flow: repository-owned FlowPilot skill must be synced to the
  local installed skill after source validation.
