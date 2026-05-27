## Why

Live FlowPilot evidence from `run-20260527-101902` showed the same PM package
disposition defect after multiple earlier hardening rounds: a foreground PM
commit recorded the newer `rework_requested` package body, then daemon
role-output replay used older durable ledger evidence for the same package
identity and crashed on a fresh different-body conflict. The final state could
also split authority between the canonical disposition artifact and the
external-event idempotency ledger.

The previous repairs were too narrow. They covered semantic body-hash conflict
rejection and repair-owned replay after a blocker or PM repair transaction
already existed, but they did not cover unowned stale replay created by
foreground/daemon interleaving before a repair owner was established.

## What Changes

- Treat daemon role-output replay of an older same-package different-body PM
  disposition as stale replay evidence when a newer canonical package
  disposition is already authoritative for that semantic package identity.
- Preserve the hard conflict rule for direct intake: a same-package
  different-body disposition is not silently accepted as success and still
  requires a repair, blocker, or explicit reissue path.
- Prevent stale daemon reconciliation from appending the old disposition event,
  overwriting the canonical package artifact, or moving the idempotency ledger
  away from the canonical body.
- Extend FlowGuard models and regression gates with the unowned foreground/
  daemon interleaving branch that previous tests missed.
- Add focused tests that reproduce the historical sequence and prove the daemon
  remains live while the current package disposition remains authoritative.
- Refresh the repo-owned local FlowPilot install and validate sync before this
  change is considered complete.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `pm-package-disposition-semantics`: Adds canonical-authority semantics for
  stale unowned package-disposition replay.
- `persistent-router-daemon`: Requires daemon role-output replay to quarantine
  stale unowned package conflicts without entering `daemon_error`.
- `role-output-transaction-boundaries`: Requires replay to respect the current
  file-backed PM package disposition authority before mutating run state.
- `runtime-state`: Prevents stale state saves from merging a stale PM package
  disposition over a newer authoritative package body.
- `known-friction-regression-gates`: Expands the package-disposition friction
  family to include the historical unowned stale replay branch.

## Impact

- Affected runtime code: role-output ledger reconciliation, package-disposition
  replay classification, and stale run-state merge authority if needed.
- Affected FlowGuard models: event idempotency, control-plane friction,
  known-friction matrix, and model-test alignment.
- Affected tests: focused package-disposition role-output reconciliation and
  daemon replay tests.
- Affected sync: repo-owned installed FlowPilot skill and local install checks.
