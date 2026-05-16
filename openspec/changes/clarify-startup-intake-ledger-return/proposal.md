## Why

The startup intake prompt still says to submit the native UI result as a direct
Router action, which can mislead Controller after the Router daemon has already
projected startup work into the Controller action ledger. The wording should
point Controller back to the current Router-owned work board without teaching a
new conditional workflow.

## What Changes

- Replace direct "apply this pending action" startup-intake wording in the
  FlowPilot skill and Router-generated instruction text with a concise
  "return to Router status and Controller action ledger" instruction.
- Preserve the native startup intake sealed-body boundary: Controller still
  never reads or submits the user request body text.
- Add focused prompt-boundary regression coverage so daemon-scheduled startup
  rows do not expose stale direct-apply wording.
- Keep existing Controller receipt mechanics, Router reconciliation, and
  startup UI payload contracts unchanged.

## Capabilities

### New Capabilities

- `startup-intake-control-plane-prompt`: Prompt and regression boundaries for
  native startup intake handoff after the Router daemon owns startup progress.

### Modified Capabilities

- None.

## Impact

- Affected files: `skills/flowpilot/SKILL.md`,
  `skills/flowpilot/assets/flowpilot_router.py`, focused router/runtime tests,
  prompt-boundary checks, and local installed FlowPilot skill synchronization.
- No public API changes, no new dependency, no new ledger, and no change to the
  native startup intake result schema.
