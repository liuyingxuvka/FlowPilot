## Why

The current FlowPilot run can keep doing valid runtime work while losing
role continuity. PM, Reviewer, and worker responsibilities may be assigned to
new agent identities even when the same role already has usable current-run
context. When a blocker then creates repair work, PM can see that a blocker
exists but may not receive enough concrete repair context before the next
packet is issued.

That creates a practical loop risk: agents keep exchanging formally valid
packets, but the repair packet asks for another summary or decision instead of
the specific corrected artifact that would clear the blocker.

## What Changes

- Prefer the current-run active agent for every same FlowPilot responsibility
  when issuing a new lease, unless the prior same-responsibility agent is
  explicitly unavailable or superseded.
- When any responsibility must move to a new agent identity, attach a
  current-run role memory seed before the packet can be opened.
- Add role memory to the role-only packet opening surface without exposing
  sealed packet bodies to Controller.
- Enrich PM repair-decision packets with the blocker recommendation, target
  packet, stale evidence, prior PM repair decision, and an explicit repair
  deliverable contract.
- Enrich repair reissue packets so the recipient knows the required fresh
  output and that a repair summary alone cannot satisfy the blocked gate.
- Detect repeat blocker families and surface loop/escalation context in PM
  repair packets and repair reissue packets.

## Capabilities

### New Capabilities

- `role-continuity-memory`: Defines current-run same-role reuse and replacement
  memory injection.

### Modified Capabilities

- `blocker-repair-policy`: Requires repair packets to carry concrete repair
  recommendations, deliverable contracts, and repeat-loop context.

## Impact

- Runtime role leases and handoff/open-packet surfaces in
  `skills/flowpilot/assets/flowpilot_core_runtime`.
- PM repair-decision and sender-reissue packet generation.
- Focused complete-runtime tests for role reuse, replacement memory, PM repair
  context, and repeated blocker context.
- FlowGuard/OpenSpec validation, local installed FlowPilot sync, and git
  evidence after implementation.
