## Why

Synthetic AI replay and hard-gate packs now cover many protocol-level mistakes, but they do not yet prove the control plane recovers from realistic infrastructure failures such as stale locks, half-written artifacts, launcher/daemon death, duplicate heartbeat wakeups, or peer-run stop attempts.

This change adds a bounded control-plane failure canary so those failures are tested as first-class FlowPilot scenarios before broader live testing.

## What Changes

- Add a finite control-plane failure canary matrix covering lock, persistence, daemon/launcher, heartbeat/resume, peer-run isolation, and terminal-fence recovery scenarios.
- Add executable runtime tests that inject realistic control-plane failure artifacts without damaging live user state.
- Register the canary in the fast validation tier and model-test alignment evidence.
- Preserve the confidence boundary: these tests prove current modeled control-plane recovery paths, not every possible operating-system or hardware failure.

## Capabilities

### New Capabilities

- `control-plane-failure-canary`: Defines the required canary scenarios, evidence fields, known-bad rejection checks, and runtime replay expectations for realistic FlowPilot control-plane failure injection.

### Modified Capabilities

- None.

## Impact

- Adds simulation and test files under `simulations/` and `tests/`.
- Updates fast-tier registration and model-test alignment plans/results.
- Updates FlowGuard adoption records and local install evidence.
- Does not change production runtime behavior unless a canary exposes a defect that requires a minimal root fix.
