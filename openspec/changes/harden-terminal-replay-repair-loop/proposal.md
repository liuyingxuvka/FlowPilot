## Why

The previous terminal backward replay repair made a valid blocking Reviewer
result become a semantic blocker instead of a mechanical contract failure, but
the full return path is still incomplete. After PM chooses
`repair_current_scope`, runtime opens a replacement terminal review packet that
does not carry the terminal replay `segment_targets`, and `router_next_action`
can return `close_project` while a current terminal repair/reissue packet is
still open.

This creates false confidence: focused tests prove blocker recording and happy
terminal closure, but they do not prove that a failed final review can be
repaired, replayed, cleared, and closed.

## What Changes

- Preserve terminal backward replay context on current-scope repair packets for
  terminal replay blockers.
- Make current open terminal repair/reissue packets preempt `close_project`.
- Add regression coverage for the full loop: valid terminal block, PM repair
  decision, terminal repair/replay packet, Reviewer rerun, blocker clearing,
  accepted replay, and final closure.
- Extend fake E2E and model-test alignment evidence so the public current
  contract covers the full repair-return loop, not only first blocker capture.
- Keep the new-only current contract. No legacy result shape, compatibility
  alias, or fallback parser is introduced.

## Capabilities

### Modified Capabilities

- `terminal-ledger`: Terminal replay blocker repair must produce a later
  current passing replay before final closure can complete.
- `flowpilot-control-plane-contract-kernel`: Terminal replay current-scope
  repair packets must preserve runtime-issued target context.
- `hard-gate-coverage-matrix`: Hard-gate evidence must include the complete
  final-review rejection repair loop.

## Impact

- Runtime/router behavior in
  `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`.
- Fake E2E behavior in
  `skills/flowpilot/assets/flowpilot_core_runtime/fake_e2e.py`.
- Focused tests under `tests/`.
- FlowGuard model-test alignment rows and generated result artifacts under
  `simulations/`.
- FlowGuard adoption logs, topology, and installed-skill sync after validation.
