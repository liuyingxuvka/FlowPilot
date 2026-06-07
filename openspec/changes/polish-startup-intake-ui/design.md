## Context

The current startup intake UI is a native WPF dialog implemented in PowerShell. Its behavior is already governed by the interactive startup intake model: the dialog captures the work request, records background-collaboration authorization, writes no-BOM artifacts, and keeps the request body sealed from the Controller.

The user explicitly wants a minimal visual polish pass, not a new Cockpit, a multi-pane redesign, or a change to runtime semantics. Language and developer support controls already live inside the settings popup and should remain there.

## Goals / Non-Goals

**Goals:**

- Make the existing single-window startup UI feel more mature and less like a temporary form.
- Tighten proportions by reducing oversized header and request field dimensions.
- Make ordinary borders/backgrounds neutral and reserve the brand accent for primary/focus/enabled states.
- Refresh main-screen copy with more precise FlowPilot run language.
- Verify through screenshots, FlowGuard startup intake checks, WPF smoke, and install sync checks.

**Non-Goals:**

- No product architecture changes.
- No new panels, route dashboard, Cockpit, or post-startup monitoring UI.
- No schema, artifact, sealed-body, or Controller visibility changes.
- No movement of language or developer-support controls out of settings.
- No dependency or framework change.

## Decisions

- Keep the current WPF/PowerShell implementation and current control tree. This avoids introducing a new UI stack for a polish-only change.
- Change design tokens and dimensions directly in the active startup intake script and mirror the same values in the desktop preview script. This keeps the repo-owned preview aligned with the formal UI.
- Use neutral gray for ordinary chrome and a muted FlowPilot purple only for the primary button, enabled toggle, hover, and focus states. This lowers the saturated purple form feeling while preserving brand recognition.
- Reduce the request box height instead of changing its placement. The input remains the central task surface but no longer dominates the full window.
- Capture screenshots from the real WPF surface where possible. If process-window capture targets the host console instead of the WPF child window, treat that capture as invalid and use a repo-owned screenshot or full-desktop/verified capture path.

## Risks / Trade-offs

- Visual changes can accidentally make text clip at smaller window sizes -> keep minimum window constraints and verify the WPF smoke plus screenshots.
- Copy changes can drift from tests or install checks -> run focused startup UI checks and install self-check after edits.
- Installing from a dirty shared tree can absorb unrelated peer changes -> inspect git status before and after sync, and keep git staging scoped to this change.
