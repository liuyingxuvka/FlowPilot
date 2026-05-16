## Why

FlowPilot already distinguishes card ACKs from formal work outputs, and
Controller standby already reminds roles and checks liveness during report/result
waits. The current gap is between those two mechanisms: a role can ACK a work
card, stop without submitting the expected Router output, and then be treated as
a role-liveness recovery case even when the better first action is to reissue
the same work attempt.

This change hardens the existing flow rather than creating a new one.

## What Changes

- Strengthen every work-card and packet ACK instruction so ACK is explicitly
  only receipt, and any card/packet that asks for an output, report, decision,
  result, or blocker must continue immediately after ACK and submit through the
  Router-directed runtime path.
- Extend wait-target status so Controller can distinguish:
  - still working: continue standby;
  - no output and not still working: Router reissues the same work attempt;
  - unavailable role: role recovery;
  - ambiguous status: PM/control-blocker handling.
- Add a Router-owned no-output reissue path for the current wait. The
  replacement row is durable before the old wait is marked `superseded`.
- Preserve role recovery for missing, cancelled, unknown, unresponsive, or lost
  roles.

## Impact

- Runtime/cards: FlowPilot runtime kit card headers, packet body templates, and
  runtime-generated ACK instructions.
- Runtime behavior: `skills/flowpilot/assets/flowpilot_router.py` wait-target
  summary and no-output reissue event handling.
- Models/checks: prompt-boundary and two-table scheduler FlowGuard coverage.
- Tests: focused router runtime tests for no-output reissue before role
  recovery and prompt text coverage.
- Installation: sync repository-owned FlowPilot skill to the local installed
  skill after verification.
