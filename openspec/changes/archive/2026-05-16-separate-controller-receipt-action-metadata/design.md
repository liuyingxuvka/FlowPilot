## Context

FlowPilot now uses a daemon-owned Controller action ledger as the normal runtime work board. The Controller table prompt and role card say that each ready row is completed by performing the row work and writing a `controller-receipt`; `next`, `apply`, and `run-until-wait` are diagnostic or explicit repair tools in daemon mode.

The implementation still stores the original Router action metadata inside each `runtime/controller_actions/*.json` record. That metadata defaults to `apply_required: true`, mirrors that into `next_step_contract.apply_required`, and includes display/startup wording such as "before applying". For daemon-scheduled Controller rows, this creates a mixed contract: the row says receipt, while nested metadata says apply.

## Goals / Non-Goals

**Goals:**
- Make Controller ledger rows expose a single completion path: perform the row work and write `controller-receipt`.
- Preserve original Router pending-action metadata for diagnostics and direct Router apply paths.
- Keep true pending Router actions, including the native startup intake UI boundary, on the direct apply path when they are not projected as Controller ledger rows.
- Add model and test coverage for daemon rows, display confirmation rows, role spawn rows, heartbeat rows, terminal summary rows, and direct pending actions.
- Sync the installed local FlowPilot skill after source changes.

**Non-Goals:**
- Remove `apply_action` or the CLI `apply` command.
- Change Controller authority, Router ownership, startup gates, heartbeat semantics, or role packet/body boundaries.
- Rework unrelated router scheduler or startup ACK join behavior.

## Decisions

1. Add a Controller-ledger action projection.
   - Decision: before writing `controller_actions/*.json`, create a Controller-visible action view that includes `controller_completion_command: "controller-receipt"` and `controller_completion_mode: "controller_action_ledger_receipt"`.
   - Rationale: this fixes the confusing metadata at the boundary where Controller actually reads it, without changing direct Router pending actions.
   - Alternative rejected: globally set `apply_required` default to false. That would weaken real direct apply actions and many existing payload contracts.

2. Preserve original Router apply semantics under explicit names.
   - Decision: for Controller rows, move original `apply_required` and `next_step_contract.apply_required` to `router_pending_apply_required` and `next_step_contract.router_pending_apply_required`, while setting the Controller-visible `apply_required` values to false.
   - Rationale: diagnostics can still see the original pending-action intent, but Controller no longer gets contradictory instructions.

3. Rewrite Controller-visible wording.
   - Decision: display, startup role-spawn, heartbeat, terminal summary, and Controller role-card wording will say "write a Controller receipt" when the action is in the Controller ledger path.
   - Rationale: text instructions must match machine-readable metadata. Leaving "before applying" in Controller-visible rows keeps the bug alive.

4. Keep direct pending action wording separate.
   - Decision: direct Router pending action helpers may continue to say "apply this pending action" where the Controller is interacting with `run-until-wait`/`apply` before or outside ledger projection.
   - Rationale: the bug is not the existence of apply; it is leaking apply semantics into receipt rows.

## Risks / Trade-offs

- [Risk] Tests or downstream scripts may assert `apply_required: true` in Controller action JSON. → Mitigation: update tests to assert the new projected fields and preserve original intent under `router_pending_apply_required`.
- [Risk] Direct pending actions accidentally lose their apply contract. → Mitigation: add regression coverage for startup intake/direct actions.
- [Risk] Wording-only cleanup misses machine-readable metadata. → Mitigation: test both persisted `controller_actions/*.json` and generated action fields.
- [Risk] Large model regressions take time. → Mitigation: run focused tests first and launch heavyweight FlowGuard model checks using the repository background log contract.

## Migration Plan

1. Add the projection helper and use it in the Controller action writer.
2. Update Controller-visible wording in Router-generated metadata and cards.
3. Add focused router/runtime tests and a prompt/contract FlowGuard check for the new metadata boundary.
4. Run focused tests, then launch full meta/capability regressions in `tmp/flowguard_background/`.
5. Run install sync/check so the installed local skill is source-fresh.
