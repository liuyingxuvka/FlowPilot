## Context

FlowPilot already separates passive waits from ordinary Controller action rows, but monitor display still uses `current_wait.waiting_for_role` as the most visible ownership signal. That field is derived from `run_state.pending_action`, so it can become null while the real work is still held by a packet recipient, passive reconciliation state, Router calculation, or Controller internal bookkeeping.

Controller needs a single monitor concept that names the live responsibility owner in plain language. The older wait metadata remains useful for compatibility, reminders, and diagnostics, but it should not be the primary status headline.

## Goals / Non-Goals

**Goals:**

- Add one controller-facing `current_work` object to daemon status and current status summary payloads.
- Derive `current_work` from the best available live responsibility source, not only from `pending_action`.
- Make packet-holder and passive reconciliation cases visible when `pending_action` is null.
- Keep legacy wait metadata available for existing reminder/liveness logic.
- Add focused tests and FlowGuard coverage for the null-wait gap.

**Non-Goals:**

- Do not remove or rename existing `current_wait` or `waiting_for_role` fields in this change.
- Do not change packet routing authority, sealed body access, reminder timing, or PM decision authority.
- Do not broaden Controller approval power; this is display/status projection, not route advancement.

## Decisions

1. **Use one primary object: `current_work`.**

   The monitor will expose `current_work` with owner identity, owner kind, source, task label, and diagnostics. This gives Controller a single question to inspect: "who is currently supposed to be working?"

   Alternative considered: add `formal_wait` and `effective_owner`. That is accurate internally but too confusing for the monitor because it preserves two competing headlines.

2. **Derive ownership by priority.**

   The helper will derive `current_work` in this order:

   - pending executable action or pending passive wait target;
   - active packet holder when the packet ledger says a role owns the current packet;
   - unresolved passive wait from Controller action ledger or router scheduler ledger;
   - internal Controller/Router duty from daemon/current action state;
   - standby/idle when no nonterminal work owner can be found.

   The priority keeps active Router action decisions first while fixing the null gap after `pending_action` is cleared.

3. **Separate display labels from authority fields.**

   `current_work.owner_key` and `current_work.owner_kind` are machine-readable. `current_work.owner_label` and `current_work.task_label` are concise user-facing strings. Controller uses the machine fields for liveness checks and the labels for the monitor.

4. **Do not infer completion from ownership.**

   `current_work` only names the current responsibility owner. It does not mark a role complete, approve PM decisions, or satisfy waits.

## Risks / Trade-offs

- [Risk] The new field could drift from legacy `current_wait` metadata. -> Mitigation: derive both from common runtime inputs and test cases where `current_wait` is null but packet/passive ownership exists.
- [Risk] Controller-local or Router-local work may look like an external role wait. -> Mitigation: include `owner_kind` values such as `controller`, `router`, `role`, `user`, and `none`.
- [Risk] Existing integrations may still read `waiting_for_role`. -> Mitigation: preserve all existing fields and add `current_work` as a non-breaking projection.
- [Risk] Broad meta/capability checks are expensive. -> Mitigation: run focused model/tests first and launch heavyweight regressions in the background using the repository log contract.

## Migration Plan

1. Add the OpenSpec contract and focused FlowGuard model coverage.
2. Implement a helper in `flowpilot_router.py` that builds `current_work`.
3. Attach `current_work` to daemon status, foreground standby payloads, and current status summary.
4. Add runtime tests for packet-holder and passive reconciliation cases with `pending_action` null.
5. Sync the installed local FlowPilot skill from the repository source and audit it.
6. Run focused tests plus background meta/capability regressions before commit.

## Open Questions

- None. The display term is `current_work` in JSON and "current work owner/current task" in human-facing copy.
