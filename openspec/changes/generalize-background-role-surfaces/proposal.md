## Why

FlowPilot's startup authorization and role-binding prompts should remain portable across AI hosts instead of implying a Codex-specific implementation. The current wording is mostly host-neutral, but it does not clearly direct AI executors to choose isolated, addressable role surfaces when several background mechanisms are available.

## What Changes

- Generalize the startup background-collaboration wording away from product-specific host names.
- Refine AI-facing role-binding instructions to prefer host-supported, isolated, addressable role surfaces for runtime-requested responsibilities.
- Remove unnecessary Codex-specific wording from live role mechanism help text.
- Keep the startup result schema and answer enum unchanged; no compatibility fields or legacy mapping layers are added.

## Capabilities

### New Capabilities
- `host-neutral-role-surfaces`: FlowPilot can authorize and record background role work through any current host's isolated, addressable execution surface.

### Modified Capabilities

## Impact

- Startup intake UI copy and preview copy.
- FlowPilot activation prompt and protocol/reference wording.
- Role-binding templates and startup/recovery prompt text that defines live role surface selection.
- Focused FlowGuard model text, install checks, and startup/runtime tests that assert the portable wording.
