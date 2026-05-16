## Context

FlowPilot has a role-recovery path for missing, completed, or unhealthy background roles. Today the recovery path can restore the role and then notify PM through a freshness card, even when the next required action is purely mechanical: re-open a missed ACK, resume an already-authorized report, or settle evidence that already exists.

The runtime already has the information needed for mechanical replay: controller action rows, router scheduler rows, card ACK ledgers, packet ledgers, role memory packets, and role recovery reports. The design should use that metadata without letting Controller read sealed bodies, infer from chat history, or invent work.

## Goals / Non-Goals

**Goals:**

- Restore or replace a role from current-run memory before any replayed obligation is issued.
- Let Router scan the recovered role's outstanding waits and classify each as already satisfied, needing ACK replay, needing formal output replay, or needing PM escalation.
- Preserve original wait order when several replacement obligations are needed.
- Supersede old wait rows only after the replacement row is durably created.
- Keep successful mechanical recovery out of the PM decision path unless ambiguity or semantic conflict exists.
- Add executable FlowGuard coverage before production behavior changes.

**Non-Goals:**

- Controller will not choose or invent new work.
- Router will not read sealed packet or result bodies to decide replay.
- This change will not alter PM authority for route changes, acceptance changes, conflicting outputs, or unclear ownership.
- This change will not merge or rewrite unrelated active OpenSpec changes.

## Decisions

### Router owns obligation replay

After `recover_role_agents` writes a successful recovery report, Router will run a mechanical replay planner for the recovered role. The planner reads only controller-visible metadata and emits one of these outcomes for each outstanding obligation:

- `settled_existing_ack`
- `settled_existing_output`
- `replacement_ack_required`
- `replacement_output_required`
- `pm_escalation_required`

Alternative considered: notify PM after every recovery. That is safer but over-serializes mechanical work and makes PM acknowledge facts Router can prove.

### Existing evidence is settled before replay

Router first checks expected ACK and output envelopes. If an expected envelope exists, belongs to the current run, matches the expected role/card/packet/contract, and has a valid hash, Router settles the original wait row without asking the role to repeat it.

Alternative considered: always replay after recovery. That risks duplicate side effects and makes late but valid evidence harder to account for.

### Replacement rows are durable before old rows are superseded

When evidence is missing or invalid, Router creates a replacement row linked to the original row. Only after that replacement row is written and visible in the controller action ledger does Router mark the original row `superseded` with `superseded_by`.

Alternative considered: mark the old row superseded first and then enqueue the replacement. That can drop the obligation if enqueue fails.

### Multiple replacement obligations keep original order

The planner sorts candidate waits by their original scheduler/controller order. It issues replacement rows in that order and stops on the first replacement creation failure.

Alternative considered: issue all replay rows in a batch. That is faster but can reorder prerequisites, especially ACK-before-work and review-before-activation sequences.

### PM is an escalation target, not a mechanical ACK sink

PM receives a decision card only when Router cannot mechanically classify continuation: conflicting outputs, packet ownership ambiguity, repeated failed recovery, route/acceptance drift, or invalid evidence whose remediation changes task semantics.

Alternative considered: preserve the current PM freshness card as a default post-recovery barrier. That keeps conservative authority separation but adds latency and conflates mechanical freshness with PM decisions.

## Risks / Trade-offs

- Replacement rows could duplicate work if evidence validation is too narrow. Mitigation: validate current run, role, card/packet identity, expected return kind, and hash before replay.
- Superseding old rows could hide useful audit history. Mitigation: keep `replaces`, `superseded_by`, `replacement_reason`, and `original_order` on both rows.
- Existing dirty parallel work may already change the scheduler model. Mitigation: keep this change scoped and integrate with existing ledgers rather than broad refactors.
- Background model checks can be expensive. Mitigation: run focused new checks first and launch heavyweight meta/capability regressions in background with the repository's standard log contract.

## Migration Plan

1. Add or update FlowGuard model coverage for role-recovery replay ordering, settlement, replacement durability, and PM escalation boundaries.
2. Implement Router helpers that collect recovered-role wait obligations from current run metadata.
3. Add replacement row creation and superseding links.
4. Change successful recovery flow to invoke replay planning before PM freshness notification.
5. Keep PM escalation as a fallback when mechanical replay cannot preserve semantics.
6. Run focused tests and FlowGuard checks, then run heavyweight regression commands in background using `tmp/flowguard_background/` artifacts.
