## Why

`flowpilot_router_controller_scheduler_standby.py` still mixes the foreground
standby public loop with the smaller state-policy matrix that decides standby
state, foreground mode, return permission, patrol requirement, and stop
permission. The matrix is small enough to receive full boundary coverage, so it
should be a leaf model boundary instead of staying inside the broader standby
owner.

## What Changes

- Add a standby state-policy child module.
- Keep existing standby facade helper names available from the parent module.
- Cover the child policy with a full Cartesian input matrix test.
- Add source-audited model/test alignment evidence for the new leaf boundary.

## Impact

- No public FlowPilot facade, CLI, or JSON schema behavior changes.
- The standby parent remains the compatibility surface.
- The extracted child becomes the directly tested boundary for state and mode
  outputs.
