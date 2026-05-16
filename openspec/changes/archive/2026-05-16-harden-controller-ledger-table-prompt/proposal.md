## Why

Long-running FlowPilot runs can leave Controller repeatedly reading its own
action ledger after the original role prompt has aged out of attention. The
ledger should carry a compact table-local reminder so Controller keeps its
role, row order, foreground attachment, and continuous standby duty clear.

## What Changes

- Add a compact English Controller table prompt to the generated
  `runtime/controller_action_ledger.json` before the action rows.
- Require Controller to process ready rows from top to bottom, write receipts,
  and mark rows complete before moving onward.
- Strengthen foreground guidance: as long as FlowPilot is still running,
  Controller must keep the foreground Controller work attached instead of
  stopping because the table is quiet, blocked, waiting for a user, waiting for
  repair, or waiting for another role.
- Clarify that the final `continuous_controller_standby` row is a continuous
  monitoring duty, not a finishable checklist item. During standby, Controller
  watches Router status and the action ledger, keeps the visible Codex plan in
  sync, and returns to top-to-bottom row processing when Router exposes new
  Controller work.
- Add focused model/runtime/install checks so future prompt edits cannot weaken
  the table-local reminder or standby semantics.

## Capabilities

### New Capabilities

- `controller-ledger-table-prompt`: Controller-facing action ledger prompt and
  continuous standby semantics for long-running FlowPilot control loops.

### Modified Capabilities

- None.

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md`
- `skills/flowpilot/assets/runtime_kit/cards/system/controller_resume_reentry.md`
- `scripts/check_install.py`
- focused FlowGuard/runtime tests and result files
- local installed FlowPilot skill synchronization
