## Context

The old FlowPilot router had role binding recovery and PM memory rehydration
ideas, but the new current-run runtime leases responsibilities through
`flowpilot_new.py lease-agent` and `flowpilot_core_runtime.host`. That current
path does not automatically reuse a same-role agent and does not seed a
replacement with role memory.

The implementation must stay current-runtime only. It must not revive old
router artifacts as authority, infer old fields, or silently translate legacy
role-binding layouts.

## Decision: Role Continuity Is Current-Run Ledger State

The new runtime stores a compact `role_continuity` section inside the current
run ledger. For each role, it records:

- the preferred current-run agent id;
- the latest lease id and packet id;
- whether the role was reused or replaced;
- a bounded, controller-safe memory summary made from packet envelopes,
  result ids, outcomes, blocker ids, and PM repair decisions.

The ledger remains the authority. Historical files may be audit context only.

## Decision: Same Responsibility Reuses Before Spawning

When a new lease is requested for any FlowPilot responsibility, the runtime
first checks that responsibility's current-run role slot. If the slot has a
usable agent id and the role has not reported an unavailable or superseded
liveness state, the lease uses that same agent id even if the caller supplied a
fresh candidate id.

If the prior role is unavailable, cancelled, expired, superseded, or explicitly
not reusable, the lease uses the requested new agent id and attaches a memory
seed to the lease.

## Decision: Memory Is Role-Visible, Not Controller-Sealed Body Access

The role handoff may tell Controller that memory exists, but the full memory
summary is included only in `open-packet`, which is already addressed to the
assigned role. The memory summary must not include sealed packet or result body
text. It is limited to public ids, statuses, role, packet objective, blocker
class, recommendation text, and current repair context.

## Decision: Repair Packets Must Name The Correct Work

PM repair-decision packets include the reviewer/system recommendation and the
current repair target. Repair reissue packets include the original output
contract and a concrete completion contract:

- submit a fresh result for the current repair packet;
- replace or repair the named target evidence;
- do not submit only a repair explanation unless the original output contract
  explicitly asks for an explanation;
- preserve the required recheck role and gate.

## Risks

- Too much memory could leak sealed content. The implementation must summarize
  metadata only.
- Reusing a dead agent could stall a packet. Host liveness status must mark
  unavailable states as non-reusable and force replacement memory.
- Repeat-loop detection can be over-sensitive. It should be advisory context
  for PM, not an automatic terminal stop.
