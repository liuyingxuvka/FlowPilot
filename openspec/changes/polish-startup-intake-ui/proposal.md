## Why

The native startup intake dialog is functional, but the current visual balance makes it feel more like a temporary form than a mature desktop software entry point. The user wants a minimal polish pass that improves perceived quality without changing the startup workflow, runtime contract, settings placement, or controller visibility rules.

## What Changes

- Tighten the existing WPF window proportions, header scale, input field height, and spacing.
- Refine the neutral color system so ordinary borders/backgrounds are calmer and the FlowPilot accent is reserved for primary action, enabled state, hover, and focus.
- Update the main action and request-field copy to sound more like a controlled FlowPilot run while preserving the existing inputs.
- Keep language and developer-support controls inside the existing settings popup.
- Preserve all startup intake artifacts, schemas, body sealing, background-collaboration requirement, and cancel/block behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `interactive-startup-intake`: Adds a visual-polish requirement for the existing native startup intake dialog while preserving current startup behavior and evidence contracts.

## Impact

- Affected source: `skills/flowpilot/assets/ui/startup_intake/flowpilot_startup_intake.ps1`
- Affected preview: `docs/ui/startup_intake_desktop_preview/flowpilot_startup_intake.ps1`
- Affected documentation asset if refreshed: `assets/readme-screenshots/startup-intake.png`
- Validation: startup intake FlowGuard checks, WPF smoke, screenshot inspection, install sync/audit/check.
