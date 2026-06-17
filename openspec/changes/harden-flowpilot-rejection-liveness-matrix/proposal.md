## Why

Recent FlowPilot incidents showed the same bug class recurring across different
role and artifact families: an AI output is mechanically or semantically
insufficient, the runtime rejects or blocks part of it, but the next control
step can still repeat the same action or payload without new repair
information. Existing focused fixes now cover contradictory FlowGuard evidence
and empty parent-scope repair, but FlowPilot still needs a parent
rejection/liveness matrix that proves rejected outputs either receive precise
repair guidance and return with a semantic delta, or become an explicit
blocker, repair route, user-required wait, or break-glass condition.

## What Changes

- Add a FlowPilot rejection/liveness matrix that spans runtime packet/result
  contracts, FlowGuard reports, Reviewer/PM repair reports, fake AI outputs,
  startup intake, route repair, terminal replay, and live-run projection.
- Require each supported rejection path to return actionable repair feedback:
  missing fields or body, current subject identity, responsible owner, legal
  command or event, and the minimum valid structured shape.
- Require post-rejection continuation to prove a semantic delta, a current
  external/user event, or a terminal blocker/repair/stop disposition before the
  same action can continue.
- Harden live-run projection so repeated nonterminal actions above the
  configured threshold cannot be reported as mesh-green or safe-to-continue
  while no new current-run event exists.
- Extend synthetic/fake AI coverage so contract-derived malformed payload cells
  are generated for multiple packet/result families, not only acceptance-item
  and terminal replay cases.
- Bind the new model, TestMesh, runtime checks, and historical current-run
  replay evidence into model-test alignment and topology.

## Capabilities

### New Capabilities

- `flowpilot-rejection-liveness-matrix`: parent capability for cross-contract
  malformed-output rejection, feedback quality, next-attempt semantic-delta,
  stuck absorption, and live-run projection obligations.

### Modified Capabilities

- `router-process-liveness`: live process projection must surface repeated
  same-action/no-new-event loops as blockers rather than green continuation.
- `multiround-fake-ai-control-rehearsal`: fake AI rehearsals must include
  contract-derived malformed payload cells and no-delta retry rows.
- `synthetic-agent-coverage-matrix`: synthetic coverage must own required
  rejection/liveness cells with current evidence and preserve the non-live
  confidence boundary.
- `flowguard-boundary-test-alignment`: model-test alignment must bind the new
  rejection/liveness obligations to owner code contracts and executable tests.
- `flowpilot-packet-review-flow`: packet/result review flow must preserve
  precise rejection feedback and reject same-payload continuation after a
  rejected output.
- `controller-break-glass-repair`: break-glass eligibility must include
  repeated current-run control-plane no-progress loops after normal repair or
  reissue paths fail.

## Impact

- Runtime and packet/result contract code under
  `skills/flowpilot/assets/flowpilot_core_runtime/`.
- Runtime cards and prompt coverage under
  `skills/flowpilot/assets/runtime_kit/cards/`.
- New and existing FlowGuard models, TestMesh runners, result artifacts, and
  model-test alignment plans under `simulations/`.
- Runtime, fake AI, historical replay, lifecycle guard, model mesh, and
  synthetic coverage tests under `tests/`.
- FlowGuard project topology and adoption logs after model/test/runtime
  changes are validated.
