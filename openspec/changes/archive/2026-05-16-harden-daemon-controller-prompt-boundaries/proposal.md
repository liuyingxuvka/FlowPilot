## Why

FlowPilot's daemon-first startup and two-table runtime are already present, but several Controller-facing prompts still use broad phrases such as "return to the router", "continue the router loop", and "prefer run-until-wait". Those phrases can make the foreground assistant manually drive Router after the daemon has taken over the normal metronome.

This change hardens only prompt and prompt-generated text so the model reads the current architecture consistently: after the minimal bootloader starts or attaches the daemon, normal progress comes from daemon status and the Controller action ledger; Controller performs exposed rows, writes receipts, and otherwise stays in standby.

## What Changes

- Clarify launcher guidance so manual `next/apply/run-until-wait` is pre-daemon, diagnostic, test, or explicit repair behavior, not normal daemon-mode progress.
- Replace broad heartbeat/manual-resume wording that says to "return to router" or "continue the router loop" with daemon attachment and Controller-ledger processing language.
- Harden Controller role-card guidance for unclear next steps, `controller_local_action`, and table row processing.
- Harden generated Controller ledger prompts so row completion means row action plus Controller receipt, never a router metronome command between rows.
- Add focused FlowGuard coverage for prompt-induced manual Router metronome hazards, including heartbeat resume, empty table standby, unclear next step, and row-to-row processing.
- Do not change daemon scheduling, duplicate row reconciliation, PM/Reviewer/Worker authority, or non-prompt runtime behavior in this change.

## Capabilities

### New Capabilities

- `daemon-controller-prompt-boundaries`: Defines prompt-level authority boundaries after daemon startup, including Controller ledger processing, standby behavior, heartbeat/manual resume re-entry, and diagnostic-only Router commands.

### Modified Capabilities

None.

## Impact

- Affected prompt sources:
  - `skills/flowpilot/SKILL.md`
  - `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md`
  - `templates/flowpilot/heartbeats/hb.template.md`
  - generated prompt text in `skills/flowpilot/assets/flowpilot_router.py`
- Affected validation:
  - focused FlowGuard model/checks under `simulations/`
  - prompt/source coverage checks where practical
  - local install sync and audit checks
- Non-impact:
  - no change to startup daemon ordering;
  - no fix for repeated Controller-row exposure after done receipts;
  - no Meta or Capability heavyweight model run by user direction;
  - no release, publish, or deployment action.
