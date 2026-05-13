# Missing ACK Report Recovery Plan

## Risk Intent Brief

Use FlowGuard for this change because it modifies Router event ingress,
role-report acceptance, card-return recovery, and evidence validity. The
protected harm is accepting a report that was written before the addressed role
proved it read the system card, or turning a mechanical missing-ACK problem
into a generic PM/control blocker instead of a same-role reread/re-ACK/re-report
flow.

## Optimization Sequence

| Step | Optimization Point | Concrete Change | Proof Before Production Change |
| --- | --- | --- | --- |
| 1 | Model missing-ACK report arrival | Represent a normal role report arriving while its required card return is still pending and no valid ACK file exists. | FlowGuard known-bad hazard must fail if the report is accepted. |
| 2 | Model quarantine semantics | Represent that the premature report is recorded only as quarantined audit evidence, never as the accepted event body. | FlowGuard hazard must fail if quarantined evidence is later used as a pass. |
| 3 | Model same-role recovery | Represent Router asking the same role/agent to open the card, submit ACK, and then submit a fresh report. | FlowGuard safe path must pass without generic PM escalation. |
| 4 | Model timestamp/order proof | Represent that the accepted report must be submitted after the valid ACK resolution. | FlowGuard hazard must fail if an old pre-ACK report is revived after ACK. |
| 5 | Model invalid and incomplete ACKs | Preserve wrong-role, wrong-hash, and incomplete bundle ACK rejection. | Existing and new hazards must fail if these ACKs accept a report. |
| 6 | Model dependency awareness | A pending ACK for an unrelated role/card must not quarantine a valid unrelated report. | FlowGuard hazard must fail if unrelated pending returns invalidate the report. |
| 7 | Model escalation boundary | Repeated same-role ACK recovery failure or missing action path may escalate to PM, but the first missing-ACK report should not. | FlowGuard hazard must fail if first recoverable missing-ACK report creates a generic PM blocker. |
| 8 | Implement one Router ingress branch | Replace the recoverable missing-ACK hard blocker with report quarantine plus a same-role card-return recovery result. | Targeted runtime tests must prove no event flag is set and no active control blocker is created. |
| 9 | Sync local install and git | Synchronize the local installed FlowPilot skill and commit locally only. | Install sync, audit, check, and local git commit pass; no GitHub push. |

## Bug Risks To Catch First

| Risk | What Could Go Wrong | FlowGuard Coverage |
| --- | --- | --- |
| R1 | A role report is accepted even though the required card ACK is missing. | `missing_ack_report_must_quarantine_and_recover` |
| R2 | A report written before ACK is later revived after ACK appears. | `accepted_report_must_follow_valid_ack` |
| R3 | A quarantined report is used as reviewer/PM/pass evidence. | `quarantined_report_is_audit_only` |
| R4 | Router escalates the first recoverable missing-ACK report to PM instead of same-role recovery. | `recoverable_missing_ack_uses_same_role_recovery_first` |
| R5 | Router accepts wrong-role, wrong-hash, invalid, or incomplete bundle ACK before accepting the report. | `pre_event_ack_rejects_invalid_or_incomplete_ack` |
| R6 | A pending ACK for an unrelated card/role quarantines a valid unrelated report. | `missing_ack_recovery_is_dependency_scoped` |
| R7 | The same role ACKs but does not submit a new post-ACK report, and Router accepts the old report. | `accepted_report_must_follow_valid_ack` |
| R8 | Repeated recovery failure loops forever without PM escalation. | `recoverable_missing_ack_uses_same_role_recovery_first` |

## Minimal Production Repair Shape

Add one Router event-ingress branch after valid pre-event ACK reconciliation and
before unresolved-card-return blocker creation:

1. Detect whether the incoming normal role event is blocked by the first
   pending card return.
2. If a valid ACK file exists, use the existing pre-event ACK reconciliation
   path and continue.
3. If no valid ACK exists and the pending return targets the same role implied
   by the incoming event, do not accept the event.
4. Persist a quarantine/audit record for the attempted report payload without
   setting the event flag or treating the body as evidence.
5. Return a same-role recovery result that points at the existing card or bundle
   return action: the role must open the card/bundle, submit ACK, then submit a
   new report.
6. Preserve generic control blockers only for non-recoverable cases: unknown
   dependency, unrelated pending return, missing card action, repeated recovery
   failure, or role recovery needs.

This keeps Router as the mechanical evidence authority and keeps PM out of
ordinary missing-ACK repair.
