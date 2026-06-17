---
schema_version: flowpilot.result_body.v1
packet_id: <packet-id>
run_id: <run-id>
route_id: <route-id>
node_id: <node-id>
completed_by_role: <same-as-result-envelope-completed_by_role>
completed_by_agent_id: <agent-id-or-background-agent-id>
result_body_hash_algorithm: sha256
controller_may_read: false
recipient_must_verify_current_assignment_before_opening: true
---

---
FLOWPILOT_RESULT_IDENTITY_BOUNDARY_V1: true
completed_by_role: <completed_by_role>
recipient_role: <same-as-result-envelope-next_recipient>
recipient_identity: I completed this as `<completed_by_role>` for this packet result only; the next recipient must read it only as the result envelope recipient.
allowed_scope: Read and review only this result body, its result envelope, and the source packet evidence after verifying current assignment, body hash, and completed_by_role identity.
forbidden_scope: I did not approve gates unless my role is the approver; do not act as another role, bypass the current runtime, hide unresolved issues, or relabel this result.
required_return: If this is the current packet result, submit completion through `flowpilot_new.py submit-result` for the assigned lease and packet. Later review, PM decision, FlowGuard operator response, blocker, or reissue/repair mail follows the current FlowPilot packet path. Result producers do not advance route state directly.
controller_aside: The result envelope may include an optional `controller_aside` for a short Controller-only process/status note. It is not evidence, not a finding, not a recommendation, not an approval, and not a runtime event source.
---

# Result Body

This file contains the detailed result for the packet. The controller must not
read, summarize, repair, execute, or complete this result body. The controller
only handles runtime-authorized result envelope metadata after the current
runtime exposes it. Current packet completion is submitted through the runtime
lifecycle, not to Controller.

The result envelope may carry an optional `controller_aside` for brief
Controller process/status context only. Do not use it for formal work content,
evidence, findings, recommendations, decisions, approvals, or report details.
The runtime preserves the field as metadata and must not use it to satisfy waits or
derive events.

Before reading this file, reviewer, PM, or FlowGuard operator must verify that
the current assignment targets the reader role and the result body hash matches
the result envelope. If the check fails, do not read this body; return the
unopened result envelope for PM reissue or repair.

## Status

<completed|blocked|needs_pm>

## Commands Or Probes Run

- <command-or-probe>

## Files Or Artifacts Changed

- <path-and-summary>

## Artifact Handoff

- artifact_refs: <formal-output-or-evidence-paths-and-hashes-or-none>
- changed_paths: <created-or-edited-paths-or-none>
- output_contract_id: <packet-envelope-output_contract.contract_id>
- inspection_notes: <what-PM-reviewer-or-FlowGuard operator-should-inspect-directly>
- pm_suggestion_items: <candidate-items-or-empty-list>
- consultation_note: <bounded-advice-only-or-not-applicable>

## Evidence

- <evidence-path-screenshot-log-model-result-or-output>

## Proof of Depth

When the source packet includes a `Low-Quality Success Guard`, explain how the
work proved the named hard part instead of only producing existence-only
evidence. Use `not applicable` only when the source packet explicitly says the
guard classification is `none`.

- hard_part_addressed: <hard-part-or-not-applicable>
- thin_success_shortcut_avoided: <what-was-not-done-casually-or-not-applicable>
- depth_evidence_refs: <paths-commands-screenshots-direct-review-or-not-applicable>
- why_existence_only_evidence_is_not_the_claim: <brief-explanation-or-not-applicable>

## Acceptance Item Result Matrix

For every source packet `Acceptance Item Projection` row, return one matching
row. Missing rows mean the packet did not close its assigned acceptance slice.

- acceptance_item_id: <acc-id>
- status: <accepted|blocked|waived|superseded|not_applicable_with_reason>
- evidence_refs: <paths-commands-screenshots-review-or-waiver-ref>
- quality_floor_met: <true|false>
- low_quality_failure_patterns_checked: <list>
- remaining_gap_or_repair_needed: <none-or-specific-gap>

## Supplemental Repair Result Matrix

For every source packet `Supplemental Repair Projection` row, return one
matching row. Missing rows mean the packet did not close its assigned terminal
supplemental repair item.

- supplemental_contract_id: <contract-id-or-none>
- repair_item_id: <repair-item-id-or-none>
- status: <accepted|blocked|waived|superseded|not_applicable_with_reason>
- evidence_refs: <paths-commands-screenshots-review-or-waiver-ref>
- required_repair_satisfied: <true|false>
- remaining_gap_or_repair_needed: <none-or-specific-gap>

## Structure Hygiene Delta

When the source packet includes a `Structure Hygiene Delta Requirement`, report
what changed structurally inside this packet boundary. Use `none` only when the
source packet explicitly declared no expected surfaces and no fallback-like path,
compatibility branch, duplicate adapter, stale generated artifact, or
maintenance layer was introduced, touched, or retained.

- introduced_surfaces: <surface-ids-or-none>
- removed_surfaces: <surface-ids-or-none>
- rejected_surfaces: <surface-ids-or-none>
- preserved_negative_rejection_evidence: <surface-ids-or-none>
- retained_owned_current_runtime_recovery: <surface-ids-or-none>
- retained_owned_maintenance_layers: <surface-ids-or-none>
- unowned_or_unvalidated_surfaces: <must-be-none-or-list-blocking-items>
- old_artifacts_used_as_current_completion_evidence: false
- validation_evidence_refs: <paths-commands-review-or-none>
- sunset_or_next_disposition: <criteria-or-not-applicable>

## Findings

- <finding-or-observation>

## Open Issues

- <issue-or-none>

## PM Note

For worker or FlowGuard operator packet results, include a short PM-facing note.
This note is decision-support, not gate approval and not permission to expand
scope. For other result types, write `not applicable`.

- In-scope quality choice: <simpler-or-higher-quality-choice-used-inside-this-packet-boundary-or-none>
- PM consideration: <out-of-scope-better-idea-route-risk-or-simplification-opportunity-for-PM-or-none>

## PM Suggestion Items

Use `none` when there are no PM suggestion candidates. Otherwise list candidate
`flowpilot.pm_suggestion_item.v1` entries for PM disposition in
`pm_suggestion_ledger.jsonl`. Include source role, source output reference,
summary, classification, authority basis, and evidence references. Do not copy
sealed body content into the suggestion item. Worker-origin items are advisory
only and must not use `current_gate_blocker`. FlowGuard operator items may use
`current_gate_blocker` only for formal model-gate findings inside the
PM-requested model boundary.

## Skill Standard Result Matrix

For every inherited child-skill standard id declared in the source packet,
include one row. Use `none` only when the source packet's `Inherited Skill
Standards` section says no child-skill standards apply.

| standard_id | status | evidence_path | waiver_reason | note |
| --- | --- | --- | --- | --- |
| <standard-id-or-none> | <done|not_applicable|waived|blocked> | <path-or-null> | <reason-or-null> | <short-note> |

## Child Skill Use Evidence

For every active child-skill binding declared in the source packet, include one
row proving that the source skill or required reference was opened and the
current-node slice was applied. If an applicable child-skill standard was
stricter than the PM packet, record that the stricter standard was followed or
cite the explicit PM waiver. Use `none` only when the source packet's `Active
Child Skill Bindings` section says no active child-skill bindings apply.

| binding_id | source_skill_path_opened | referenced_paths_opened | node_slice_scope_used | stricter_standard_applied_or_waived | evidence_path | note |
| --- | --- | --- | --- | --- | --- | --- |
| <binding-id-or-none> | <path-or-none> | <paths-or-none> | <scope-or-none> | <applied|waived|not_applicable> | <path-or-null> | <short-note> |

## Role Skill Use Evidence

For every role skill use binding declared in the source packet, role-work
request, child-skill gate manifest, or node acceptance plan, include one row
proving that the named role opened the source skill and references, used the
skill only for the declared role context, and produced the affected output or
gate evidence. Use `none` only when the source packet's `Role Skill Use
Bindings` section says no role skill use bindings apply.

| binding_id | used_by_role | use_context | source_skill_path_opened | referenced_paths_opened | affected_output_or_gate | evidence_path | stricter_standard_applied_or_waived | checker_role | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <binding-id-or-none> | <role-or-none> | <context-or-none> | <path-or-none> | <paths-or-none> | <artifact-or-gate-or-none> | <path-or-null> | <applied|waived|not_applicable> | <role-or-none> | <short-note> |

## Contract Self-Check

- source_output_contract_id: <packet-envelope-output_contract.contract_id>
- required_sections_present: <true|false>
- evidence_matches_contract: <true|false>
- unmet_contract_items: <items-or-none>
- self_check_decision: <satisfied|blocked|needs_pm>

## Requested Next Recipient

<human_like_reviewer|project_manager|flowguard_operator>

