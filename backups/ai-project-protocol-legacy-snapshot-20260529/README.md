# AI Project Protocol Legacy Snapshot

This backup preserves the tracked repository content before the clean AI
project protocol kernel work started on 2026-05-29.

## Snapshot

- Source commit: `85337f0883600cdb1b2341e9a654d8b2725acf7d`
- Source commit subject: `Adopt FlowPilot runtime path evidence`
- Archive: `flowguardprojectautopilot-tracked-head-20260529.zip`
- Archive SHA256:
  `3A02BAAB3CE8671FCA3050FF8C1F7E1F815F0588EDEE9347C1C7A7D56C9B5EA5`

## Use Boundary

This snapshot is a read-only legacy reference for the new AI project protocol
kernel. The new protocol may reuse visual assets, startup-panel references,
test case names, and known failure cases from the old system.

The new protocol must not inherit old runtime state, compatibility routes,
stale evidence, old role ownership assumptions, or old fixed-agent topology.

## Allowed Reuse

- `assets/brand/flowpilot-icon-default.png`
- `assets/readme-screenshots/startup-intake.png`
- `skills/flowpilot/assets/brand/flowpilot-icon-default.png`
- Startup-panel wording and layout ideas, only after they are restated in the
  new protocol contract.
- Historical failure modes such as missing ACK, ACK without usable output,
  stale route output, weak review, stale evidence reuse, and final closure
  gaps.

## Explicit Non-Reuse

- `.flowpilot/` local run state.
- Old route state as current truth.
- Old FlowPilot role count or fixed-agent assignment as a requirement.
- Any old validation result unless it is rerun under the new model and recorded
  as fresh evidence.
