## Why

The clean new FlowPilot runtime can resume from a ledger, but it does not yet
prove that a nonterminal run will keep a Controller-style guard alive instead
of silently ending after it reports the next action. This matters now because
the rebuilt runtime is intended to replace old heavy monitor behavior without
bringing back old UI, fixed-role, or compatibility surfaces.

## What Changes

- Add a small lifecycle guard to the new FlowPilot runtime:
  - terminal completion is only final when `controller_stop_allowed` is true;
  - nonterminal status returns a guard action rather than allowing a foreground
    controller to claim it is done;
  - resume/manual wake loads the current run, packet ledger, leases, wait
    state, and next action before deciding what can proceed;
  - waits are classified as healthy wait, overdue ACK, overdue result, inactive
    lease, stale result, repeated same action, or control-plane stuck;
  - recovery is expressed as current-run guard/recovery evidence, not prose in
    chat and not old router compatibility.
- Add public CLI/status support for guard patrol and manual resume on the new
  runtime path.
- Extend fake-host rehearsal and FlowGuard models to cover interruption,
  resume, missing ACK, no result, inactive lease, late/stale result, repeated
  next action, and terminal-stop gating.
- Keep the new dynamic-agent model. Do not restore a heavy monitor UI, fixed
  six-person topology, old router authority, or retired side commands.

## Capabilities

### New Capabilities
- `new-flowpilot-lifecycle-guard`: Minimal Controller-style lifecycle guard for
  the new black-box FlowPilot runtime, covering nonterminal stop prevention,
  resume rehydration, wait patrol, recovery classification, stale/late result
  quarantine, control-plane stuck detection, and terminal stop authorization.

### Modified Capabilities
- `multiround-fake-ai-control-rehearsal`: Fake AI rehearsal must prove
  lifecycle interruption and recovery branches, not only the happy path.
- `runtime-ledger-persistence`: The current-run ledger must persist guard
  snapshots, patrol decisions, and terminal stop authority.

## Impact

- Affected code:
  - `skills/flowpilot/assets/ai_project_runtime/runtime.py`
  - `skills/flowpilot/assets/ai_project_runtime/run_shell.py`
  - `skills/flowpilot/assets/flowpilot_new.py`
  - fake-host rehearsal and runtime tests
  - FlowGuard model/check files under `simulations/`
- Affected validation:
  - OpenSpec validation for this change and all specs
  - focused unit tests for the new runtime lifecycle guard
  - fake AI rehearsal through public runtime surfaces
  - FlowGuard recursive/new-entrypoint/model-test alignment checks
  - local install sync/audit/check-install and background meta/capability
    regressions
- No new third-party dependency or UI requirement is planned.
