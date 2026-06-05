## Why

FlowPilot accepted FlowGuard evidence can be reviewed later, but worker-created
scripts may currently bind execution to a specific FlowPilot packet or active
phase. A reviewer replay can then surface a control-plane failure, after which
PM `stop_for_user` may be reissued instead of becoming an immediate hard wait.

## What Changes

- Add one shared package rule that scripts, checkers, and evidence generators
  must be replayable and must not gate execution on a specific FlowPilot packet
  id, active packet, or one-time phase.
- Clarify reviewer prompt policy so reviewers default to inspecting existing
  run results and only rerun scripts when evidence is critical, suspicious, or
  needs adversarial replay.
- Clarify PM blocker policy so control-plane blockers prefer the existing
  Controller break-glass repair lane before user stop.
- Harden `stop_for_user` so stopped blockers remain a hard user wait unless the
  user explicitly requests recovery.

## Capabilities

### New Capabilities

- `replayable-control-repair`: Replayable package artifacts, reviewer replay
  policy, control-plane repair routing, and hard user-stop behavior.

### Modified Capabilities

- `blocker-repair-policy`: PM repair policy now prioritizes Controller
  break-glass for control-plane blockers before user stop.
- `controller-break-glass-repair`: Existing break-glass capability becomes the
  preferred route for replayability and package-control failures.
- `flowpilot-packet-review-flow`: Reviewer review policy now defaults to
  existing evidence inspection and reserves reruns for targeted replay.

## Impact

- Runtime kit cards and packet instructions under `skills/flowpilot/assets`.
- Runtime stopped-blocker recovery in `flowpilot_core_runtime/runtime.py` and
  `flowpilot_new.py`.
- Focused tests and FlowGuard models covering replayability, PM control-plane
  routing, and hard user-stop behavior.
