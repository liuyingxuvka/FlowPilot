## Why

The current synthetic exception packages cover high-risk single branches, but
real FlowPilot failures often come from several valid-looking AI actions,
repairs, stale ledgers, and terminal gates interacting across a whole run. We
need system-level replay packages that prove the workflow can constrain bad or
partial AI work back into the control plane instead of only proving isolated
guards.

## What Changes

- Add system-level synthetic replay packages that chain fake AI output,
  control-plane classification, PM repair or escalation, resume/route recovery,
  and terminal completion gates.
- Cover six new story classes: valid envelope with bad content, stacked
  control blockers, failed PM repair loops, restart/stale-state replay,
  peer/parallel write interference, and final completion gate rejection.
- Extend the synthetic coverage matrix so system-level replay rows identify
  the recovery loop they prove, not only the local failure mode.
- Refresh model-test alignment and fast-tier evidence after the new packages
  are added.
- Keep local installed FlowPilot synchronized after validation and commit the
  finished local repository state.

## Capabilities

### New Capabilities

- `systemic-synthetic-agent-replay`: governs end-to-end fake AI replay stories
  that verify FlowPilot can constrain bad AI work back into legal control-plane
  recovery paths.

### Modified Capabilities

- `synthetic-agent-coverage-matrix`: matrix rows now distinguish local
  exceptional replay from system-level replay and record the recovery loop
  proven by each story package.

## Impact

- Affected tests: synthetic agent trace replay tests, synthetic coverage matrix
  tests, relevant router runtime slices, fast tier, and model-test alignment.
- Affected FlowGuard artifacts: synthetic coverage matrix JSON,
  model-test-alignment JSON, and background Meta/Capability check artifacts.
- Affected install flow: repository-owned `flowpilot` skill sync, install audit,
  and install check must run after source validation.
