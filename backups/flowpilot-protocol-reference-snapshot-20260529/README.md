# FlowPilot Protocol Reference Snapshot

This backup preserves tracked repository content before the FlowPilot protocol
kernel work started on 2026-05-29.

## Snapshot

- Source commit: `85337f0883600cdb1b2341e9a654d8b2725acf7d`
- Source commit subject: `Adopt FlowPilot runtime path evidence`
- Archive: `flowpilot-tracked-head-20260529.zip`
- Archive SHA256:
  `3A02BAAB3CE8671FCA3050FF8C1F7E1F815F0588EDEE9347C1C7A7D56C9B5EA5`

## Use Boundary

This snapshot is a read-only reference for the FlowPilot protocol kernel. The
current protocol may reuse visual assets, startup-panel references, test case
names, and known failure cases after restating them in the current contract.

The current protocol must not inherit prior runtime state, unsupported
transition routes, stale evidence, prior role ownership assumptions, or prior
fixed-agent topology.

## Allowed Reuse

- `assets/brand/flowpilot-icon-default.png`
- `assets/readme-screenshots/startup-intake.png`
- `skills/flowpilot/assets/brand/flowpilot-icon-default.png`
- Startup-panel wording and layout ideas, only after they are restated in the
  current protocol contract.
- Historical failure modes such as missing ACK, ACK without usable output,
  stale route output, weak review, stale evidence reuse, and final closure
  gaps.

## Explicit Non-Reuse

- `.flowpilot/` local run state.
- Prior route state as current truth.
- Prior FlowPilot role count or fixed-agent assignment as a requirement.
- Any prior validation result unless it is rerun under the current model and
  recorded as fresh evidence.
