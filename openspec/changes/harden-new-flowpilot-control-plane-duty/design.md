## Context

The new `flowpilot_new.py` runtime is intentionally thinner than the old Router daemon. It keeps authority in the current-run ledger, dynamic leases, sealed packets, lifecycle guard, and foreground duty. The last live audits exposed a remaining gap: the runtime can know what the next action is while the foreground Controller either stops too early, misclassifies a safe internal action as stuck, or accepts a misparsed PM repair decision.

Old FlowPilot already had useful control-plane patterns: safe internal actions were folded by `run-until-wait`, foreground standby polled internal state every second, role waits patrolled every 60 seconds, and waiting was represented as an action instead of a prompt reminder. This change borrows those patterns without restoring the old monitor UI, fixed team, or daemon authority.

## Goals / Non-Goals

**Goals:**

- Add one small new-runtime action classifier so `router_next_action` results are interpreted consistently.
- Fold safe router-internal mechanical actions before the foreground Controller sees a wait boundary.
- Treat "black box is doing internal work" as a short internal wait/fold path, not as a stuck control plane.
- Keep role-agent waits on the existing 60-second patrol duty and require current liveness evidence before replacement.
- Require structured PM repair decision fields for hard lifecycle choices.
- Make status projection read-only for lifecycle guard history; patrol remains the explicit refresh path.
- Extend FlowGuard and regression evidence for the generalized miss class, not only the observed packet.

**Non-Goals:**

- Do not restore the old Router daemon, old Controller action ledger, kanban monitor, or non-startup UI as required new-runtime authority.
- Do not reintroduce fixed four-role or six-role execution as a hard requirement.
- Do not let the foreground Controller read sealed packet or result bodies to decide progress.
- Do not solve product-quality or semantic-review completeness in this change except where parser decisions affect control flow.

## Decisions

### Decision: Classify every new-runtime next action before acting

`RuntimeAction` will be classified into:

- `router_internal`: safe mechanical work the black box can apply itself.
- `role_dispatch`: an open packet needs a role lease.
- `role_wait`: an assigned/ACKed packet is waiting on ACK, progress, result, or liveness.
- `recovery`: repair/reissue/replacement/assignment-race work is due.
- `user_required`: the run is paused or explicitly requires user input.
- `terminal`: final closure permits foreground return.
- `controller_external`: any non-internal action that must be surfaced instead of guessed.

This avoids the false binary of "Controller has a button" versus "the system is stuck." The foreground only gets a durable wait or dispatch boundary after internal work has settled.

### Decision: Add a bounded new-runtime `run_until_wait`

The new runtime will add a bounded fold loop equivalent in spirit to the old `run-until-wait`. It will consume only allowlisted internal actions with deterministic side effects, such as:

- creating preplanning gate packets,
- materializing route nodes,
- creating node acceptance plan packets,
- creating node task packets,
- creating FlowGuard/review/validation/PM disposition/closure packets,
- attempting final closure when all prerequisites are present.

The loop stops before role dispatch, role wait, user-required, recovery requiring external evidence, or terminal return. It records folded actions so tests and status can explain what happened.

### Decision: Use short internal folding and long role patrol

Internal black-box work is not a user-facing wait. It is folded immediately by the bounded loop, with a one-second-style diagnostic policy only when a future command needs polling. Role work remains a 60-second patrol duty through the existing `wait_patrol` payload. Replacement still depends on explicit inactive/dead/no-output evidence, not repeated status reads alone.

### Decision: PM repair decisions must be structured

PM repair decisions are hard lifecycle inputs. The parser will accept only:

- a JSON object with `decision`, `repair_decision`, or `recovery_option`;
- or a strict key-value token such as `decision=same_node_repair` or `decision: same_node_repair`.

Rationale text is never scanned for lifecycle aliases. If the body lacks a structured decision, the PM repair result is blocked as a payload contract error and routed back through the same PM repair packet family instead of guessing. `block` and `stop` in prose no longer map to `stop_for_user`.

### Decision: Stopped and repairing blocker states are mutually exclusive

`stop_for_user` sets the blocker and packet into a stopped state and blocks further repair packet creation for that blocker. `same_node_repair` keeps the blocker in repairing/awaiting-recheck state and creates fresh repair work. Router logic must not ignore stopped blockers while continuing the same repair chain.

### Decision: Status is projection-only

`status` will render current state without appending lifecycle guard history, incrementing repeated counts, or writing new lifecycle events. `patrol`, `resume`, `lease-agent`, `ack`, `progress`, `submit-result`, and repair commands remain stateful. Console files can still be materialized from real writes, but a user asking "status" must not change whether the run is considered stuck.

## Risks / Trade-offs

- Internal folding could hide too much work -> keep a narrow allowlist, max-hop limit, and folded-action report.
- Structured PM decisions may reject older informal bodies -> PM repair packets already state allowed decisions; rejection is safer than guessing the wrong lifecycle state.
- Read-only status may leave console files stale between stateful commands -> status can render directly from the ledger without writing, and stateful commands keep materialized projections current.
- Adding another model/test family increases maintenance load -> keep the model focused on control-plane boundaries and map it to a small set of ordinary tests.

## Migration Plan

1. Record this OpenSpec change and FlowGuard model-miss boundary.
2. Add model/check coverage for structured decisions, internal folding, stopped-blocker consistency, status read-only, and fake public-control rehearsal.
3. Implement parser, action classifier, internal fold loop, status read-only path, and stopped-blocker guard.
4. Update fake rehearsal to drive through the same public control fold path.
5. Run focused tests and model checks first, then broader regression/background checks.
6. Sync the installed FlowPilot skill only after focused validation passes; record install/git status and remaining confidence boundaries.

Rollback strategy: keep the change active, do not sync installed skill as complete, and revert only this change's scoped files if focused validation fails.
