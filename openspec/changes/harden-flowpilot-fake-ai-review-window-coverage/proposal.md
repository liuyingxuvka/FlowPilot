## Why

Recent real-run evidence showed that FlowPilot can reject invalid outputs while
still failing to surface every runtime-enforced rule in the first AI-visible
packet contract. The next hardening pass must upgrade existing fake-AI and
Cartesian coverage so it proves the whole loop: visible contract, synthetic AI
mistake, precise runtime rejection, repairable reissue, reviewer repair loop,
and controlled break-glass threshold.

## What Changes

- Extend the existing contract-driven fake AI responder so malformed syntax,
  format violations, missing projected obligations, finite-option mistakes,
  partial repairs, corrected retries, and repeated same-family failures are
  generated from packet-local contracts instead of hand-written fixtures.
- Require AI-visible contract projection tests to compare runtime validator
  obligations with `current_handoff_contract.required_report_contract`,
  minimal shapes, finite options, type requirements, and current active IDs.
- Harden planning and node-acceptance contract projection so acceptance item
  owner coverage and acceptance-item projection are visible before the first
  role response and repairable after rejection.
- Require reviewer packets to expose a runtime-checkable review window and
  enough authorized upstream material for the declared window, while preserving
  the existing Reviewer -> PM repair node -> Reviewer recheck path.
- Extend fake-AI and contract-exhaustion matrices to cover format rejection,
  no-pollution blocking, corrected second retry, one-to-four same-class
  retries, fifth-attempt break-glass, and break-glass body-read grants.
- Update prompt/card wording only where the current cards do not already expose
  the contract boundary; do not introduce a parallel reviewer framework, legacy
  fallback, or PM override of Reviewer quality decisions.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `synthetic-agent-coverage-matrix`: add fake-AI responder owned Cartesian
  cells for syntax, format, projection, retry, repair, reviewer-window, and
  break-glass threshold coverage.
- `multiround-fake-ai-control-rehearsal`: require multi-round fake AI
  rehearsals to use the contract-driven responder for bad output, corrected
  retry, and repeated same-family behavior.
- `flowpilot-control-plane-contract-kernel`: require runtime-enforced
  validator obligations to be visible through AI-facing structured contracts
  before the first response, including current active IDs and finite options.
- `formal-gate-review-standards`: require reviewer packets to carry a
  runtime-checkable review window and authorized material scope, not only prose
  instructions.
- `blocker-repair-policy`: keep Reviewer hard blockers on the normal PM repair
  path and require repair/recheck evidence before escalation.
- `controller-break-glass-repair`: cover same-family fifth-attempt escalation
  and controlled sealed-body grants for recovery, without making break-glass a
  normal completion path.
- `tiered-flowpilot-test-validation`: require the upgraded focused tests,
  FlowGuard models, install checks, and topology refresh as current evidence
  before claiming this hardening complete.

## Impact

- Affected code: contract-driven fake AI responder, core packet/result
  contracts, runtime contract feedback, reviewer packet metadata/material
  projection, and BreakGlass recovery boundaries.
- Affected tests/models: AI contract projection tests, high-standard control
  flow tests, contract exhaustion mesh, current-contract Cartesian matrix,
  reviewer active challenge/gate tests, BreakGlass tests, and install checks.
- Affected prompts/cards: reviewer and PM repair cards only where structured
  metadata needs to be explained to roles; structured metadata remains owned by
  runtime-checkable envelopes/contracts.
