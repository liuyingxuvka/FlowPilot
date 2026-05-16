## Why

FlowPilot startup currently lets PM open the full user task intake during the
startup-intake phase, before the reviewer fact report and PM startup activation
open the formal gate. This blurs the startup boundary: PM can begin task
understanding before the system has proved it is allowed to work.

## What Changes

- Split startup authorization metadata from the full user task intake.
- Keep full user task text sealed and router-owned until PM startup activation
  is approved.
- Deliver only startup answers, run identity, current-run pointers, role,
  continuation, display, and evidence metadata before startup activation.
- Expose the full `user_intake` packet as the first post-startup PM mail item
  after `startup_activation_approved`, then deliver it through the standard
  Controller relay path.
- Add FlowGuard and runtime regressions that reject early full user intake
  release or Router-only open authority, while preserving Controller
  sealed-body boundaries.

## Capabilities

### New Capabilities
- `startup-intake-boundary`: Defines when startup metadata and full user task
  intake may be exposed to PM during FlowPilot startup.

### Modified Capabilities

## Impact

- FlowPilot router startup release logic.
- PM startup-intake and startup-activation cards.
- Startup-focused FlowGuard models and tests.
- Local installed FlowPilot skill synchronization and install self-checks.
