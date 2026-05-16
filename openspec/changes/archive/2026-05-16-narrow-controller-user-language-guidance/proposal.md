## Why

The Controller already has user-facing reporting guidance, but the strongest
plain-language rule lives in one role card and a nested per-action policy. In
long foreground runs, Controller can still repeat internal Router, action,
ledger, packet, ACK, scheduler, or diagnostic terms when explaining routine
progress to the user.

The fix should stay narrow. FlowPilot should remain flexible, and technical
details should still be available when the user asks for them or when they are
needed to explain a real blocker.

## What Changes

- Strengthen the Controller role card so it defaults to explaining current work
  in user-understandable language.
- Strengthen the generated Controller action-ledger table prompt so the live
  foreground Controller sees the same reminder at the work-board level.
- Add focused install/model checks that keep this guidance present in future
  prompt edits.
- Leave route signs, Mermaid output, fixed user-report templates, new Router
  user-summary fields, and sealed-body boundaries unchanged.

## Capabilities

### New Capabilities

- `controller-user-language-guidance`: plain-language defaults for Controller
  user-facing explanations without adding a new reporting mechanism.

### Modified Capabilities

- None.

## Impact

- `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md`
- `skills/flowpilot/assets/flowpilot_router.py`
- `scripts/check_install.py`
- focused FlowGuard control-plane friction model coverage
- local installed FlowPilot skill synchronization
