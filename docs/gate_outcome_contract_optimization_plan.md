# Gate Outcome Contract Optimization Plan

## Goal

Close the FlowPilot protocol gap where a reviewer or officer can legitimately
block a gate, but the router only waits for a pass event. The repair should
cover the class of gate-outcome failures instead of patching one observed event.

## Optimization Order

| Step | Optimization | Concrete Work | Done When |
| --- | --- | --- | --- |
| 1 | Upgrade FlowGuard detection before router edits | Extend the cross-plane friction model and live audit so it scans router state, control blockers, role output status packets, and outbox event envelopes. | The current run's `reviewer_blocks_child_skill_gate_manifest` is detected as an unregistered role event. |
| 2 | Add a gate-outcome completeness check | Model every reviewer/officer gate as needing a pass path plus a non-pass path, unless the gate has an explicit structured report path that already carries sufficient/insufficient outcomes. | FlowGuard lists pass-only gate groups instead of only checking the one observed child-skill gate. |
| 3 | Centralize gate outcome contracts | Add a small router-side contract table for role gates: gate id, owner role, delivered-card flag, pass event, block/repair event, repair target, and evidence path. | The router no longer relies on scattered pass-only event lists for review gates. |
| 4 | Implement standard block handling by repair class | Route block outcomes by class: PM rewrites source artifact, same-node repair/model-miss triage, officer route repair, or terminal/evidence repair. | A block records a file-backed report, clears stale pass state, and sends the next action to the correct repair owner. |
| 5 | Add tests per contract class | Add parameterized checks that pass outcomes advance and block outcomes route to repair without being treated as pass. | The tests cover the observed child-skill manifest block and at least one representative gate from each repair class. |
| 6 | Sync local installation | After repo tests pass, sync the repository-owned FlowPilot skill into the local installed skill and run the install audit. | Local repo and local installed version agree; no GitHub push is performed. |

## Bug Classes The Upgraded Model Must Catch

| ID | Possible Bug | Why It Matters | FlowGuard/Test Obligation |
| --- | --- | --- | --- |
| B1 | Role output event exists in outbox/status but is absent from `EXTERNAL_EVENTS`. | The router cannot record a real blocker, so it waits forever for pass. | Live audit must scan `mailbox/outbox/events` and `role_output_status` and fail on unknown role events. |
| B2 | A reviewer/officer gate has only a pass event and no non-pass route. | Any legitimate blocker becomes invisible or pressures the role to fake a pass. | Gate outcome completeness audit must flag pass-only review/officer event groups. |
| B3 | A block event is registered but not allowed in the current pending wait. | The event exists but is still unusable at the exact time the role needs it. | Runtime test must assert the pending action includes both pass and non-pass outcomes for the gate. |
| B4 | A block event records as success/approval. | A failed review could accidentally advance the route. | Tests must assert block reports do not set pass flags and stale downstream approvals are cleared. |
| B5 | A block has no repair owner. | The route exits pass-only mode but then becomes stuck. | Model and tests must assert the next action routes to PM, officer repair, or controlled stop. |
| B6 | Repair rerun keeps stale pass evidence. | PM could fix an artifact while old reviewer/officer passes remain trusted. | Tests must assert affected pass flags and review artifacts are invalidated or superseded before recheck. |
| B7 | Generic event support leaks sealed report bodies to Controller. | Fixing routability must not break packet/role-output isolation. | Existing role-output and cross-plane checks must continue to enforce envelope-only visibility. |
| B8 | The model only catches the observed child-skill event. | The same protocol gap can recur at another gate. | Hazard cases must include at least one unseen pass-only reviewer gate and one officer gate. |

## Target Design

Use a lightweight Gate Outcome Contract instead of one-off patches. Each role
gate declares its pass outcome, non-pass outcome, owner role, repair class, and
evidence paths. Router waits and FlowGuard audits are derived from that contract.

The first implementation should stay conservative:

- keep existing pass events for route advancement;
- add non-pass outcomes only for gates that can actually block;
- route non-pass outcomes back to a PM or officer repair loop instead of
  marking the gate complete;
- keep Controller envelope-only and metadata-only for role outputs;
- preserve all existing local changes made by other agents.

